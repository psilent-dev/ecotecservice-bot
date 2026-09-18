"""Планировщик эскалаций и реактивации клиентов."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, or_, select

from config import settings
from database.base import async_session_maker
from database.models import ClientRequest, User
from database.repo import RequestRepo
from keyboards.inline import admin_request_actions_kb
from services.notify import notify_admins, notify_user
from texts import (
    ADMIN_ESCALATION_120,
    ADMIN_ESCALATION_30,
    INACTIVE_CLIENT_REMINDER,
)

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_bot: Bot | None = None
_pinged_30: set[int] = set()
_pinged_120: set[int] = set()
_inactive_sent_at: dict[int, datetime] = {}


def init_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создаёт и запускает планировщик фоновых задач."""
    global _scheduler, _bot
    _bot = bot
    timezone_name = settings.tz
    scheduler = AsyncIOScheduler(timezone=timezone_name)
    scheduler.add_job(
        job_escalate_stale_requests,
        "interval",
        minutes=10,
        max_instances=1,
        coalesce=True,
        id="escalate_stale_requests",
        replace_existing=True,
    )
    scheduler.add_job(
        job_inactive_clients,
        "cron",
        hour=12,
        minute=0,
        max_instances=1,
        coalesce=True,
        id="inactive_clients",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Планировщик запущен, tz=%s", timezone_name)
    return scheduler


async def shutdown_scheduler() -> None:
    """Останавливает планировщик при завершении процесса."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Планировщик остановлен")


async def job_escalate_stale_requests() -> None:
    """Каждые 10 минут пингует админов по заявкам старше 30 минут и 2 часов."""
    if _bot is None:
        return
    async with async_session_maker() as session:
        stale_120 = await RequestRepo.get_stale_new_requests(session, 120)
        stale_30 = await RequestRepo.get_stale_new_requests(session, 30)
        ids_120 = {item.id for item in stale_120}
        only_30 = [item for item in stale_30 if item.id not in ids_120]

        for request in only_30:
            if request.id in _pinged_30:
                continue
            user = await session.get(User, request.user_id)
            if user is None:
                continue
            text = ADMIN_ESCALATION_30.format(request_id=request.id)
            await notify_admins(
                _bot,
                session,
                text,
                reply_markup=admin_request_actions_kb(request.id),
            )
            _pinged_30.add(request.id)

        for request in stale_120:
            if request.id in _pinged_120:
                continue
            user = await session.get(User, request.user_id)
            if user is None:
                continue
            text = ADMIN_ESCALATION_120.format(request_id=request.id)
            await notify_admins(
                _bot,
                session,
                text,
                reply_markup=admin_request_actions_kb(request.id),
            )
            _pinged_120.add(request.id)
            _pinged_30.add(request.id)

        live_new = {item.id for item in stale_30}
        _pinged_30.intersection_update(live_new)
        _pinged_120.intersection_update(ids_120)
        await session.commit()


async def job_inactive_clients() -> None:
    """Раз в сутки напоминает клиентам без заявок более 180 дней."""
    if _bot is None:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    last_request = (
        select(
            ClientRequest.user_id,
            func.max(ClientRequest.created_at).label("last_at"),
        )
        .group_by(ClientRequest.user_id)
        .subquery()
    )
    async with async_session_maker() as session:
        result = await session.execute(
            select(User)
            .outerjoin(last_request, User.id == last_request.c.user_id)
            .where(
                User.is_blocked.is_(False),
                User.created_at <= cutoff,
                or_(
                    last_request.c.last_at.is_(None),
                    last_request.c.last_at <= cutoff,
                ),
            )
        )
        clients = list(result.scalars().all())
        text = INACTIVE_CLIENT_REMINDER
        now = datetime.now(timezone.utc)
        for client in clients:
            previous = _inactive_sent_at.get(client.id)
            if previous is not None and now - previous < timedelta(days=180):
                continue
            delivered = await notify_user(_bot, client.tg_id, text, session=session)
            if delivered:
                _inactive_sent_at[client.id] = now
        await session.commit()
