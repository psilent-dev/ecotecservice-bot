"""Профиль и бонусы клиента."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from handlers.start import ack_event, menu_kb, require_client, show_screen, start_text
from keyboards.inline import MenuCB, NavCB, bonuses_kb
from texts import BONUSES_CARD, INVITE_SHARE_TEXT, MENU_BUTTONS, PHONE_NOT_BOUND
from utils.validators import format_phone_display

router = Router(name="profile")


def referral_link(user: User) -> str:
    """Deep-link приглашения друга."""
    return f"https://t.me/{settings.bot_username}?start=ref_{user.referral_code}"


def bonuses_text(user: User) -> str:
    """Карточка бонусов."""
    return BONUSES_CARD.format(
        full_name=user.full_name,
        phone=format_phone_display(user.phone) or PHONE_NOT_BOUND,
        balance=user.bonus_balance,
        visits=user.visits_count,
        ref_link=referral_link(user),
    )


@router.callback_query(MenuCB.filter(F.action == "bonuses"))
@router.message(F.text == MENU_BUTTONS["bonuses"])
async def show_bonuses(
    event: Message | CallbackQuery,
    session: AsyncSession,
) -> None:
    """Показывает бонусы, реферальную ссылку и кнопки."""
    _message, tg_user = await ack_event(event)
    if tg_user is None:
        return
    user = await require_client(event, session, tg_user)
    if user is None:
        return
    invite = INVITE_SHARE_TEXT.format(link=referral_link(user))
    await show_screen(event, bonuses_text(user), bonuses_kb(invite))


@router.callback_query(NavCB.filter(F.action == "back"))
async def back_to_menu(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Возврат в главное меню."""
    await callback.answer()
    if callback.from_user is None:
        return
    user = await require_client(callback, session, callback.from_user)
    if user is None:
        return
    await show_screen(callback, start_text(), menu_kb(user))
