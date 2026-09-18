"""Контакты автосервиса."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.start import require_client
from keyboards.inline import contacts_kb
from texts import CONTACTS_TEXT, MENU_BUTTONS

router = Router(name="contacts")


@router.message(F.text == MENU_BUTTONS["contacts"])
async def show_contacts(message: Message, session: AsyncSession) -> None:
    """Адрес, телефон, режим работы и кнопки карты / звонка."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        return
    await message.answer(
        CONTACTS_TEXT.format(
            service_name=settings.service_name,
            address=settings.service_address,
            phone=settings.service_phone,
            hours=settings.service_hours,
        ),
        reply_markup=contacts_kb(),
    )
