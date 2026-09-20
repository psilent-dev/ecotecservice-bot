"""Массовая рассылка клиентам."""

from __future__ import annotations

import asyncio
import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from filters.admin import IsAdmin
from keyboards.reply import admin_menu_kb, cancel_kb, confirm_kb
from services.notify import notify_user
from states.admin import AdminBroadcastStates
from texts import (
    ADMIN_BROADCAST_CANCELLED,
    ADMIN_BROADCAST_CONFIRM,
    ADMIN_BROADCAST_DONE,
    ADMIN_BROADCAST_EMPTY,
    ADMIN_BROADCAST_PROMPT,
    ADMIN_MENU_BUTTONS,
    BTN_CANCEL,
    BTN_CONFIRM,
)

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())

_SEND_DELAY = 0.05


@router.message(F.text == ADMIN_MENU_BUTTONS["broadcast"])
async def broadcast_start(message: Message, state: FSMContext) -> None:
    """Запрашивает текст рассылки."""
    await state.set_state(AdminBroadcastStates.enter_text)
    await message.answer(ADMIN_BROADCAST_PROMPT, reply_markup=cancel_kb())


@router.message(AdminBroadcastStates.enter_text, F.text == BTN_CANCEL)
@router.message(AdminBroadcastStates.confirm, F.text == BTN_CANCEL)
async def broadcast_cancel(message: Message, state: FSMContext) -> None:
    """Отмена рассылки."""
    await state.clear()
    await message.answer(ADMIN_BROADCAST_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminBroadcastStates.enter_text, F.text)
async def broadcast_preview(message: Message, state: FSMContext) -> None:
    """Показывает предпросмотр и кнопки подтверждения."""
    text = (message.text or "").strip()
    if not text:
        await message.answer(ADMIN_BROADCAST_EMPTY, reply_markup=cancel_kb())
        return
    await state.update_data(broadcast_text=text)
    await state.set_state(AdminBroadcastStates.confirm)
    await message.answer(
        ADMIN_BROADCAST_CONFIRM.format(text=html.escape(text, quote=False)),
        reply_markup=confirm_kb(),
    )


@router.message(AdminBroadcastStates.confirm, F.text == BTN_CONFIRM)
async def broadcast_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Рассылает текст всем незаблокированным пользователям."""
    if message.bot is None:
        await state.clear()
        return
    data = await state.get_data()
    text = str(data.get("broadcast_text") or "").strip()
    await state.clear()
    if not text:
        await message.answer(ADMIN_BROADCAST_EMPTY, reply_markup=admin_menu_kb())
        return

    result = await session.execute(select(User).where(User.is_blocked.is_(False)))
    recipients = list(result.scalars().all())
    sent = 0
    failed = 0
    for user in recipients:
        ok = await notify_user(message.bot, user.tg_id, text, session=session)
        if ok:
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(_SEND_DELAY)

    await message.answer(
        ADMIN_BROADCAST_DONE.format(ok=sent, fail=failed),
        reply_markup=admin_menu_kb(),
    )


@router.message(AdminBroadcastStates.confirm, F.text)
async def broadcast_confirm_hint(message: Message, state: FSMContext) -> None:
    """Напоминает подтвердить рассылку кнопками."""
    data = await state.get_data()
    text = str(data.get("broadcast_text") or "")
    await message.answer(
        ADMIN_BROADCAST_CONFIRM.format(text=html.escape(text, quote=False)),
        reply_markup=confirm_kb(),
    )
