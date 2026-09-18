"""Сообщения, не попавшие в остальные хендлеры."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.start import get_or_create_user, menu_kb
from texts import MENU_MAIN, USER_BLOCKED

router = Router(name="fallback")


@router.message(StateFilter(None), F.text)
async def unknown_text(message: Message, session: AsyncSession) -> None:
    """Подсказывает меню, если пользователь не в FSM и команда неизвестна."""
    if message.from_user is None:
        return
    user, _created = await get_or_create_user(session, message.from_user)
    if user.is_blocked:
        await message.answer(USER_BLOCKED.format(phone=settings.service_phone))
        return
    await message.answer(MENU_MAIN, reply_markup=menu_kb(user))
