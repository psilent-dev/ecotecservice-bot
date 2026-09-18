"""Профиль клиента и подробности бонусов."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from database.repo import PromoRepo, UserRepo
from handlers.start import menu_kb, require_client
from keyboards.inline import NavCB, profile_kb
from texts import (
    BONUS_DETAIL_FREE_DIAG,
    BONUS_DETAIL_LOYALTY,
    BONUS_DETAIL_REFERRAL,
    BONUS_DETAILS,
    BONUS_EMPTY,
    BONUS_FREE_DIAG,
    BONUS_LOYALTY_2ND,
    BONUS_REFERRAL_10,
    BONUSES_NO_PROMOS,
    BONUSES_PROMO_ITEM,
    BONUSES_PROMO_UNLIMITED,
    MENU_BUTTONS,
    MENU_MAIN,
    PROFILE_NO_PHONE,
    PROFILE_TEXT,
)

router = Router(name="profile")


def referral_link(user: User) -> str:
    """Deep-link приглашения друга."""
    return f"https://t.me/{settings.bot_username}?start=ref_{user.referral_code}"


def bonus_lines(user: User) -> str:
    """Краткий список активных бонусов для карточки профиля."""
    lines: list[str] = []
    if user.loyalty_discount_2nd:
        lines.append(BONUS_LOYALTY_2ND)
    if user.discount_10_active:
        lines.append(BONUS_REFERRAL_10)
    if user.free_diagnostics:
        lines.append(BONUS_FREE_DIAG)
    return "\n".join(lines) if lines else BONUS_EMPTY


async def build_profile_text(session: AsyncSession, user: User) -> str:
    """Карточка профиля: контакты, визиты, бонусы и реферальная ссылка."""
    count = await UserRepo.get_referral_count(session, user.id)
    return PROFILE_TEXT.format(
        full_name=user.full_name,
        phone=user.phone or PROFILE_NO_PHONE,
        visits=user.visits_count,
        refs=count,
        bonuses=bonus_lines(user),
        ref_link=referral_link(user),
    )


async def build_bonuses_details(session: AsyncSession, user: User) -> str:
    """Подробное описание активных наград и текущих акций."""
    blocks: list[str] = []
    if user.loyalty_discount_2nd:
        blocks.append(BONUS_DETAIL_LOYALTY)
    if user.discount_10_active:
        blocks.append(BONUS_DETAIL_REFERRAL)
    if user.free_diagnostics:
        blocks.append(BONUS_DETAIL_FREE_DIAG)
    if not blocks:
        blocks.append(BONUS_EMPTY)

    promos = await PromoRepo.get_active(session)
    if promos:
        for promo in promos:
            until = (
                promo.valid_until.strftime("%d.%m.%Y")
                if promo.valid_until is not None
                else BONUSES_PROMO_UNLIMITED
            )
            blocks.append(
                BONUSES_PROMO_ITEM.format(
                    title=promo.title,
                    description=promo.description,
                    discount=promo.discount,
                    valid_until=until,
                )
            )
    else:
        blocks.append(BONUSES_NO_PROMOS)

    return BONUS_DETAILS.format(details="\n\n".join(blocks))


@router.message(F.text == MENU_BUTTONS["profile"])
async def show_profile(message: Message, session: AsyncSession) -> None:
    """Показывает карточку профиля с inline-кнопкой бонусов."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        return
    text = await build_profile_text(session, user)
    await message.answer(text, reply_markup=profile_kb())


@router.callback_query(NavCB.filter(F.action == "bonuses"))
async def show_bonuses(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Подробности по активным бонусам."""
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return
    user = await require_client(callback.message, session, callback.from_user)
    if user is None:
        return
    await callback.message.answer(
        await build_bonuses_details(session, user),
        reply_markup=profile_kb(),
    )


@router.callback_query(NavCB.filter(F.action == "back"))
async def back_to_menu(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Возврат в главное меню с reply-клавиатурой."""
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return
    user = await require_client(callback.message, session, callback.from_user)
    if user is None:
        return
    await callback.message.answer(MENU_MAIN, reply_markup=menu_kb(user))
