"""Админ: управление промо-акциями."""

from __future__ import annotations

import html
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Promo
from database.repo import PromoRepo
from filters.admin import IsAdmin
from keyboards.reply import (
    admin_menu_kb,
    cancel_kb,
    confirm_kb,
    list_kb,
    numbered_label,
    parse_numbered,
    promo_item_kb,
    skip_cancel_kb,
)
from states.admin import AdminPickStates, AdminPromoStates
from texts import (
    ADMIN_MENU_BUTTONS,
    ADMIN_PROMO_ACTIVE,
    ADMIN_PROMO_CREATED,
    ADMIN_PROMO_DELETED,
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
    BTN_ADD,
    BTN_BACK,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_DELETE,
    BTN_EDIT,
    BTN_SKIP,
    BTN_TOGGLE,
    FSM_CANCELLED,
)

router = Router(name="admin_promo")
router.message.filter(IsAdmin())

NEW_ITEM_ID = 0


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


async def show_promos(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Список акций reply-кнопками."""
    promos = await PromoRepo.list_all(session)
    await state.set_state(AdminPickStates.promos)
    lines = [ADMIN_PROMO_HEADER]
    if promos:
        lines.extend(format_promo_item(item) for item in promos)
    labels = [numbered_label(item.id, item.title) for item in promos]
    await message.answer("\n".join(lines), reply_markup=list_kb(labels, extra=[BTN_ADD]))


@router.message(F.text == ADMIN_MENU_BUTTONS["promos"])
async def promo_root(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Корень раздела промо-акций."""
    await state.clear()
    await show_promos(message, state, session)


@router.message(AdminPickStates.promos, F.text == BTN_BACK)
@router.message(AdminPickStates.promo_item, F.text == BTN_BACK)
async def promo_back(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Назад: из карточки к списку, из списка в меню."""
    current = await state.get_state()
    if current == AdminPickStates.promo_item.state:
        await show_promos(message, state, session)
        return
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminPickStates.promos, F.text == BTN_ADD)
async def promo_add_start(message: Message, state: FSMContext) -> None:
    """FSM добавления акции."""
    await state.set_state(AdminPromoStates.enter_title)
    await state.update_data(promo_id=NEW_ITEM_ID)
    await message.answer(ADMIN_PROMO_PROMPT_TITLE, reply_markup=cancel_kb())


@router.message(AdminPickStates.promos, F.text.regexp(r"^№\d+"))
async def promo_pick(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Открывает карточку акции."""
    promo_id = parse_numbered(message.text or "")
    if promo_id is None:
        return
    promo = await PromoRepo.get_by_id(session, promo_id)
    if promo is None:
        await state.clear()
        await message.answer(ADMIN_PROMO_NOT_FOUND, reply_markup=admin_menu_kb())
        return
    await state.set_state(AdminPickStates.promo_item)
    await state.update_data(promo_id=promo.id)
    await message.answer(format_promo_item(promo), reply_markup=promo_item_kb())


@router.message(AdminPickStates.promo_item, F.text == BTN_EDIT)
async def promo_edit_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """FSM редактирования акции."""
    data = await state.get_data()
    promo = await PromoRepo.get_by_id(session, int(data["promo_id"]))
    if promo is None:
        await state.clear()
        await message.answer(ADMIN_PROMO_NOT_FOUND, reply_markup=admin_menu_kb())
        return
    await state.set_state(AdminPromoStates.enter_title)
    await state.update_data(
        promo_id=promo.id,
        title=promo.title,
        description=promo.description,
        discount=promo.discount,
        valid_until=promo.valid_until.isoformat() if promo.valid_until else "",
    )
    await message.answer(ADMIN_PROMO_PROMPT_TITLE, reply_markup=cancel_kb())


@router.message(AdminPickStates.promo_item, F.text == BTN_TOGGLE)
async def promo_toggle(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Скрывает или показывает акцию."""
    data = await state.get_data()
    promo = await PromoRepo.get_by_id(session, int(data["promo_id"]))
    if promo is None:
        await state.clear()
        await message.answer(ADMIN_PROMO_NOT_FOUND, reply_markup=admin_menu_kb())
        return
    promo.is_active = not promo.is_active
    await session.flush()
    await message.answer(format_promo_item(promo), reply_markup=promo_item_kb())


@router.message(AdminPickStates.promo_item, F.text == BTN_DELETE)
async def promo_delete(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Удаляет акцию."""
    data = await state.get_data()
    deleted = await PromoRepo.delete(session, int(data["promo_id"]))
    if not deleted:
        await state.clear()
        await message.answer(ADMIN_PROMO_NOT_FOUND, reply_markup=admin_menu_kb())
        return
    await message.answer(ADMIN_PROMO_DELETED)
    await show_promos(message, state, session)


@router.message(AdminPromoStates.enter_title, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.enter_description, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.enter_discount, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.enter_valid_until, F.text == BTN_CANCEL)
@router.message(AdminPromoStates.confirm, F.text == BTN_CANCEL)
async def promo_fsm_cancel(message: Message, state: FSMContext) -> None:
    """Отмена FSM акции."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


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
    raw = (message.text or "").strip()
    valid_until = ""
    if raw not in {"", BTN_SKIP}:
        try:
            valid_until = datetime.strptime(raw, "%d.%m.%Y").date().isoformat()
        except ValueError:
            await message.answer(ADMIN_PROMO_INVALID_DATE, reply_markup=skip_cancel_kb())
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
    await message.answer(f"{preview}\n{description}", reply_markup=confirm_kb())


@router.message(AdminPromoStates.confirm, F.text == BTN_CONFIRM)
async def promo_confirm_yes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт или обновляет акцию."""
    data = await state.get_data()
    title = str(data["title"]).strip()
    description = str(data["description"]).strip()
    discount = str(data["discount"]).strip()
    raw_until = str(data.get("valid_until") or "").strip()
    valid_until = datetime.fromisoformat(raw_until).date() if raw_until else None
    promo_id = int(data.get("promo_id") or NEW_ITEM_ID)

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
            await state.clear()
            await message.answer(ADMIN_PROMO_NOT_FOUND, reply_markup=admin_menu_kb())
            return
        text = ADMIN_PROMO_UPDATED.format(title=promo.title)

    await message.answer(text)
    await show_promos(message, state, session)
