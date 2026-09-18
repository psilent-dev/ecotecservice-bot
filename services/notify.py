"""Отправка уведомлений клиентам и администраторам."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from database.repo import UserRepo

logger = logging.getLogger(__name__)

Keyboard = InlineKeyboardMarkup | ReplyKeyboardMarkup | None


async def notify_user(
    bot: Bot,
    tg_id: int,
    text: str,
    reply_markup: Keyboard = None,
    session: AsyncSession | None = None,
) -> bool:
    """Пишет пользователю. При блокировке бота помечает `is_blocked` и не бросает ошибку."""
    try:
        await bot.send_message(tg_id, text, reply_markup=reply_markup)
        return True
    except TelegramForbiddenError:
        logger.warning("Пользователь tg_id=%s заблокировал бота", tg_id)
        if session is not None:
            user = await UserRepo.get_by_tg_id(session, tg_id)
            if user is not None:
                user.is_blocked = True
                await session.flush()
        return False
    except TelegramAPIError:
        logger.warning("Не удалось написать tg_id=%s", tg_id, exc_info=True)
        return False


async def notify_admins(
    bot: Bot,
    session: AsyncSession,
    text: str,
    reply_markup: Keyboard = None,
) -> int:
    """Рассылает сообщение всем администраторам. Возвращает число успешных доставок."""
    sent = 0
    admins = await UserRepo.get_all_admins(session)
    for admin in admins:
        if await notify_user(bot, admin.tg_id, text, reply_markup=reply_markup, session=session):
            sent += 1
    return sent
