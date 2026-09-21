"""Контакты автосервиса и маршрут."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.start import ack_event, require_client, show_screen
from keyboards.inline import MenuCB, contacts_kb
from texts import CONTACTS_TEXT, MENU_BUTTONS
from utils.validators import format_phone_display

router = Router(name="contacts")


@router.callback_query(MenuCB.filter(F.action == "contacts"))
@router.message(F.text == MENU_BUTTONS["contacts"])
async def show_contacts(
    event: Message | CallbackQuery,
    session: AsyncSession,
) -> None:
    """Адрес, график, телефон мастера-приёмщика."""
    _message, tg_user = await ack_event(event)
    if tg_user is None:
        return
    user = await require_client(event, session, tg_user)
    if user is None:
        return
    await show_screen(
        event,
        CONTACTS_TEXT.format(
            service_name=settings.service_name,
            address=settings.service_address,
            hours=settings.service_hours,
            phone=format_phone_display(settings.service_phone) or settings.service_phone,
        ),
        contacts_kb(),
    )
