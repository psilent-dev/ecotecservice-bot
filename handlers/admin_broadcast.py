"""Массовая рассылка клиентам."""

from __future__ import annotations

import asyncio
import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from filters.admin import IsAdmin
from handlers.start import ack_event, show_admin_home, show_screen
from keyboards.inline import BroadcastCB, MenuCB, broadcast_confirm_kb, cancel_kb
from services.notify import notify_user
from states.admin import AdminBroadcastStates
from texts import (
    ADMIN_BROADCAST_CANCELLED,
    ADMIN_BROADCAST_CONFIRM,
    ADMIN_BROADCAST_DONE,
    ADMIN_BROADCAST_EMPTY,
    ADMIN_BROADCAST_PHOTO,
    ADMIN_BROADCAST_PROMPT,
    ADMIN_MENU_BUTTONS,
    BTN_CANCEL,
)

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_SEND_DELAY = 0.05


@router.callback_query(MenuCB.filter(F.action == "admin_broadcast"))
@router.message(F.text == ADMIN_MENU_BUTTONS["broadcast"])
async def broadcast_start(
    event: Message | CallbackQuery,
    state: FSMContext,
) -> None:
    """Запрашивает текст рассылки."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.set_state(AdminBroadcastStates.enter_text)
    await show_screen(event, ADMIN_BROADCAST_PROMPT, cancel_kb())


@router.callback_query(AdminBroadcastStates.enter_text, MenuCB.filter(F.action == "cancel"))
@router.message(AdminBroadcastStates.enter_text, F.text == BTN_CANCEL)
async def broadcast_cancel_text(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена на шаге ввода текста."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.clear()
    await show_admin_home(event, session)


async def _recipients_count(session: AsyncSession) -> int:
    result = await session.execute(select(User).where(User.is_blocked.is_(False)))
    return len(list(result.scalars().all()))


@router.message(AdminBroadcastStates.enter_text, F.photo)
async def broadcast_preview_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Предпросмотр фото-поста."""
    if not message.photo:
        return
    caption = (message.caption or "").strip() or ADMIN_BROADCAST_PHOTO
    await state.update_data(
        broadcast_text=caption,
        photo_id=message.photo[-1].file_id,
    )
    await state.set_state(AdminBroadcastStates.confirm)
    count = await _recipients_count(session)
    await message.answer_photo(
        message.photo[-1].file_id,
        caption=ADMIN_BROADCAST_CONFIRM.format(
            count=count,
            text=html.escape(caption, quote=False),
        ),
        reply_markup=broadcast_confirm_kb(),
    )


@router.message(AdminBroadcastStates.enter_text, F.text)
async def broadcast_preview(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Предпросмотр текстовой рассылки."""
    text = (message.text or "").strip()
    if not text:
        await message.answer(ADMIN_BROADCAST_EMPTY, reply_markup=cancel_kb())
        return
    await state.update_data(broadcast_text=text, photo_id="")
    await state.set_state(AdminBroadcastStates.confirm)
    count = await _recipients_count(session)
    await message.answer(
        ADMIN_BROADCAST_CONFIRM.format(count=count, text=html.escape(text, quote=False)),
        reply_markup=broadcast_confirm_kb(),
    )


@router.callback_query(AdminBroadcastStates.confirm, BroadcastCB.filter(F.action == "cancel"))
async def broadcast_cancel_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена на шаге подтверждения."""
    await callback.answer()
    await state.clear()
    await show_admin_home(callback, session)


@router.callback_query(AdminBroadcastStates.confirm, MenuCB.filter(F.action == "cancel"))
@router.message(AdminBroadcastStates.confirm, F.text == BTN_CANCEL)
async def broadcast_cancel_confirm_text(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена на шаге подтверждения."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.clear()
    await show_admin_home(event, session)


@router.callback_query(AdminBroadcastStates.confirm, BroadcastCB.filter(F.action == "send"))
async def broadcast_send(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Рассылает текст или фото всем незаблокированным."""
    await callback.answer()
    if callback.message is None or callback.message.bot is None:
        await state.clear()
        return
    data = await state.get_data()
    text = str(data.get("broadcast_text") or "").strip()
    photo_id = str(data.get("photo_id") or "").strip()
    await state.clear()
    if not text and not photo_id:
        await show_screen(callback, ADMIN_BROADCAST_EMPTY)
        await show_admin_home(callback, session)
        return

    result = await session.execute(select(User).where(User.is_blocked.is_(False)))
    recipients = list(result.scalars().all())
    sent = 0
    failed = 0
    bot = callback.message.bot
    for user in recipients:
        try:
            if photo_id:
                await bot.send_photo(user.tg_id, photo_id, caption=text or None)
                ok = True
            else:
                ok = await notify_user(bot, user.tg_id, text, session=session)
        except Exception:
            ok = False
        if ok:
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(_SEND_DELAY)

    await show_screen(
        callback,
        ADMIN_BROADCAST_DONE.format(ok=sent, fail=failed),
    )
    await show_admin_home(callback, session)


@router.message(AdminBroadcastStates.confirm)
async def broadcast_confirm_hint(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Напоминает подтвердить рассылку кнопками."""
    data = await state.get_data()
    text = str(data.get("broadcast_text") or "")
    count = await _recipients_count(session)
    await message.answer(
        ADMIN_BROADCAST_CONFIRM.format(count=count, text=html.escape(text, quote=False)),
        reply_markup=broadcast_confirm_kb(),
    )
