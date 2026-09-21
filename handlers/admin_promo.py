"""Админ: управление промо-акциями."""

from __future__ import annotations

import html
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Promo
from database.repo import PromoRepo
from filters.admin import IsAdmin
from handlers.start import ack_event, show_screen
from keyboards.inline import (
    NEW_ITEM_ID,
    ConfirmCB,
    MenuCB,
    PromoAdminCB,
    admin_menu_kb,
    cancel_kb,
    confirm_kb,
    promos_list_kb,
    skip_cancel_kb,
)
from states.admin import AdminPromoStates
from texts import (
    ADMIN_MENU_BUTTONS,
    ADMIN_PROMO_ACTIVE,
    ADMIN_PROMO_CREATED,
    ADMIN_PROMO_HEADER,
    ADMIN_PROMO_INACTIVE,
    ADMIN_PROMO_INVALID_DATE,
    ADMIN_PROMO_ITEM,
    ADMIN_PROMO_NOT_FOUND,
    ADMIN_PROMO_PROMPT_DESCRIPTION,
    ADMIN_PROMO_PROMPT_DISCOUNT,
    ADMIN_PROMO_PROMPT_TITLE,
    ADMIN_PROMO_PROMPT_VALID_UNTIL,
    ADMIN_PROMO_UPDATED,
    BONUSES_PROMO_UNLIMITED,
    BTN_CANCEL,
    BTN_SKIP,
    FSM_CANCELLED,
)

router = Router(name="admin_promo")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def format_promo_item(promo: Promo) -> str:
    """Строка акции для админ-списка."""
    until = (
        promo.valid_until.strftime("%d.%m.%Y")
        if promo.valid_until is not None
        else BONUSES_PROMO_UNLIMITED
    )
    return ADMIN_PROMO_ITEM.format(
        id=promo.id,
        title=html.escape(promo.title, quote=False),
        discount=html.escape(promo.discount, quote=False),
        valid_until=until,
        active=ADMIN_PROMO_ACTIVE if promo.is_active else ADMIN_PROMO_INACTIVE,
    )


async def show_promos(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Печатает список акций с кнопками управления."""
    promos = await PromoRepo.list_all(session)
    lines = [ADMIN_PROMO_HEADER]
    if promos:
        lines.extend(format_promo_item(item) for item in promos)
    await show_screen(event, "\n".join(lines), promos_list_kb(promos))


@router.callback_query(MenuCB.filter(F.action == "admin_promo"))
@router.message(F.text == ADMIN_MENU_BUTTONS["promos"])
async def promo_root(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Корень раздела промо-акций."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.clear()
    await show_promos(event, session)


@router.callback_query(PromoAdminCB.filter(F.action == "add"))
async def promo_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск FSM добавления акции."""
    await callback.answer()
    await state.set_state(AdminPromoStates.enter_title)
    await state.update_data(promo_id=NEW_ITEM_ID)
    await show_screen(callback, ADMIN_PROMO_PROMPT_TITLE, cancel_kb())


@router.callback_query(PromoAdminCB.filter(F.action == "edit"))
async def promo_edit_start(
    callback: CallbackQuery,
    callback_data: PromoAdminCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Запуск FSM редактирования акции."""
    await callback.answer()
    promo = await PromoRepo.get_by_id(session, callback_data.promo_id)
    if promo is None:
        await show_screen(callback, ADMIN_PROMO_NOT_FOUND)
        return
    await state.set_state(AdminPromoStates.enter_title)
    await state.update_data(
        promo_id=promo.id,
        title=promo.title,
        description=promo.description,
        discount=promo.discount,
        valid_until=promo.valid_until.isoformat() if promo.valid_until else "",
    )
    await show_screen(callback, ADMIN_PROMO_PROMPT_TITLE, cancel_kb())


@router.callback_query(PromoAdminCB.filter(F.action == "toggle"))
async def promo_toggle(
    callback: CallbackQuery,
    callback_data: PromoAdminCB,
    session: AsyncSession,
) -> None:
    """Скрывает или показывает акцию."""
    await callback.answer()
    promo = await PromoRepo.get_by_id(session, callback_data.promo_id)
    if promo is None:
        await show_screen(callback, ADMIN_PROMO_NOT_FOUND)
        return
    promo.is_active = not promo.is_active
    await session.flush()
    await show_promos(callback, session)


@router.callback_query(PromoAdminCB.filter(F.action == "delete"))
async def promo_delete(
    callback: CallbackQuery,
    callback_data: PromoAdminCB,
    session: AsyncSession,
) -> None:
    """Удаляет акцию."""
    await callback.answer()
    deleted = await PromoRepo.delete(session, callback_data.promo_id)
    if not deleted:
        await show_screen(callback, ADMIN_PROMO_NOT_FOUND)
        return
    await show_promos(callback, session)


@router.callback_query(AdminPromoStates.enter_title, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminPromoStates.enter_description, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminPromoStates.enter_discount, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminPromoStates.enter_valid_until, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminPromoStates.confirm, MenuCB.filter(F.action == "cancel"))
@router.message(AdminPromoStates.enter_title, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.enter_description, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.enter_discount, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.enter_valid_until, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.confirm, F.text == BTN_CANCEL)
async def promo_fsm_cancel(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Отмена любого шага FSM акции."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.clear()
    await show_screen(event, FSM_CANCELLED, admin_menu_kb())


@router.message(AdminPromoStates.enter_title, F.text)
async def promo_enter_title(message: Message, state: FSMContext) -> None:
    """Название акции."""
    title = (message.text or "").strip()
    if not title:
        await message.answer(ADMIN_PROMO_PROMPT_TITLE, reply_markup=cancel_kb())
        return
    await state.update_data(title=title)
    await state.set_state(AdminPromoStates.enter_description)
    await message.answer(ADMIN_PROMO_PROMPT_DESCRIPTION, reply_markup=cancel_kb())


@router.message(AdminPromoStates.enter_description, F.text)
async def promo_enter_description(message: Message, state: FSMContext) -> None:
    """Описание акции."""
    description = (message.text or "").strip()
    if not description:
        await message.answer(ADMIN_PROMO_PROMPT_DESCRIPTION, reply_markup=cancel_kb())
        return
    await state.update_data(description=description)
    await state.set_state(AdminPromoStates.enter_discount)
    await message.answer(ADMIN_PROMO_PROMPT_DISCOUNT, reply_markup=cancel_kb())


@router.message(AdminPromoStates.enter_discount, F.text)
async def promo_enter_discount(message: Message, state: FSMContext) -> None:
    """Размер скидки."""
    discount = (message.text or "").strip()
    if not discount:
        await message.answer(ADMIN_PROMO_PROMPT_DISCOUNT, reply_markup=cancel_kb())
        return
    await state.update_data(discount=discount)
    await state.set_state(AdminPromoStates.enter_valid_until)
    await message.answer(ADMIN_PROMO_PROMPT_VALID_UNTIL, reply_markup=skip_cancel_kb())


@router.message(AdminPromoStates.enter_valid_until, F.text)
async def promo_enter_valid_until(message: Message, state: FSMContext) -> None:
    """Срок действия ДД.ММ.ГГГГ или пропуск."""
    await _save_promo_until(message, state, message.text or "")


@router.callback_query(AdminPromoStates.enter_valid_until, MenuCB.filter(F.action == "skip"))
async def promo_skip_valid_until(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропуск срока действия акции."""
    await callback.answer()
    await _save_promo_until(callback, state, BTN_SKIP)


async def _save_promo_until(event: Message | CallbackQuery, state: FSMContext, raw: str) -> None:
    """Сохраняет срок и показывает предпросмотр."""
    cleaned = raw.strip()
    valid_until = ""
    if cleaned not in {"", BTN_SKIP}:
        try:
            valid_until = datetime.strptime(cleaned, "%d.%m.%Y").date().isoformat()
        except ValueError:
            await show_screen(event, ADMIN_PROMO_INVALID_DATE, skip_cancel_kb())
            return
    await state.update_data(valid_until=valid_until)
    data = await state.get_data()
    until_label = (
        datetime.fromisoformat(valid_until).strftime("%d.%m.%Y")
        if valid_until
        else BONUSES_PROMO_UNLIMITED
    )
    preview = ADMIN_PROMO_ITEM.format(
        id=int(data.get("promo_id") or NEW_ITEM_ID),
        title=html.escape(str(data["title"]), quote=False),
        discount=html.escape(str(data["discount"]), quote=False),
        valid_until=until_label,
        active=ADMIN_PROMO_ACTIVE,
    )
    description = html.escape(str(data.get("description") or ""), quote=False)
    await state.set_state(AdminPromoStates.confirm)
    await show_screen(event, f"{preview}\n{description}", confirm_kb())


@router.callback_query(AdminPromoStates.confirm, ConfirmCB.filter(F.action == "no"))
async def promo_confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    """Отказ сохранить акцию."""
    await callback.answer()
    await state.clear()
    await show_screen(callback, FSM_CANCELLED, admin_menu_kb())


@router.callback_query(AdminPromoStates.confirm, ConfirmCB.filter(F.action == "yes"))
async def promo_confirm_yes(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт или обновляет акцию."""
    await callback.answer()
    if callback.message is None:
        await state.clear()
        return
    data = await state.get_data()
    title = str(data["title"]).strip()
    description = str(data["description"]).strip()
    discount = str(data["discount"]).strip()
    raw_until = str(data.get("valid_until") or "").strip()
    valid_until = datetime.fromisoformat(raw_until).date() if raw_until else None
    promo_id = int(data.get("promo_id") or NEW_ITEM_ID)
    await state.clear()

    if promo_id == NEW_ITEM_ID:
        promo = await PromoRepo.create(
            session,
            title=title,
            description=description,
            discount=discount,
            valid_until=valid_until,
        )
        text = ADMIN_PROMO_CREATED.format(title=promo.title)
    else:
        promo = await PromoRepo.update(
            session,
            promo_id,
            title=title,
            description=description,
            discount=discount,
            valid_until=valid_until,
        )
        if promo is None:
            await show_screen(callback, ADMIN_PROMO_NOT_FOUND, admin_menu_kb())
            return
        text = ADMIN_PROMO_UPDATED.format(title=promo.title)

    await show_screen(callback, text, admin_menu_kb())
