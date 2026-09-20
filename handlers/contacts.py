"""Контакты автосервиса."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.start import menu_kb, require_client
from texts import CONTACTS_MAPS_BUTTON, CONTACTS_TEXT, MENU_BUTTONS

router = Router(name="contacts")


@router.message(F.text == MENU_BUTTONS["contacts"])
async def show_contacts(message: Message, session: AsyncSession) -> None:
    """Адрес, телефон, режим работы и ссылка на карту."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        return
    body = CONTACTS_TEXT.format(
        service_name=settings.service_name,
        address=settings.service_address,
        phone=settings.service_phone,
        hours=settings.service_hours,
    )
    body = f"{body}\n\n{CONTACTS_MAPS_BUTTON}:\n{settings.service_maps_url}"
    await message.answer(body, reply_markup=menu_kb(user))
