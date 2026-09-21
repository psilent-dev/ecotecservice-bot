"""Сообщения, не попавшие в остальные хендлеры."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.start import ack_event, get_or_create_user, menu_kb, show_screen, start_text
from keyboards.inline import MenuCB
from texts import FSM_CANCELLED, USER_BLOCKED

router = Router(name="fallback")


@router.callback_query(MenuCB.filter(F.action == "cancel"))
async def fallback_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена вне узких FSM-хендлеров — возврат в меню."""
    _message, tg_user = await ack_event(callback)
    if tg_user is None:
        return
    await state.clear()
    user, _created = await get_or_create_user(session, tg_user)
    if user.is_blocked:
        await show_screen(callback, USER_BLOCKED.format(phone=settings.service_phone))
        return
    await show_screen(callback, FSM_CANCELLED, menu_kb(user))


@router.message(StateFilter(None), F.text)
async def unknown_text(message: Message, session: AsyncSession) -> None:
    """Подсказывает меню, если команда неизвестна."""
    if message.from_user is None:
        return
    user, _created = await get_or_create_user(session, message.from_user)
    if user.is_blocked:
        await message.answer(USER_BLOCKED.format(phone=settings.service_phone))
        return
    await show_screen(message, start_text(), menu_kb(user))
