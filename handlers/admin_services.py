"""Админ: управление услугами прайса."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Service, ServiceCategory
from database.repo import ServiceRepo
from filters.admin import IsAdmin
from handlers.start import ack_event, show_admin_home, show_screen
from keyboards.inline import (
    NEW_ITEM_ID,
    ConfirmCB,
    MenuCB,
    NavCB,
    ServiceAdminCB,
    cancel_kb,
    categories_admin_kb,
    confirm_kb,
    services_list_kb,
    skip_cancel_kb,
)
from states.admin import AdminServiceStates
from texts import (
    ADMIN_MENU_BUTTONS,
    ADMIN_SERVICE_ACTIVE,
    ADMIN_SERVICE_CREATED,
    ADMIN_SERVICE_DELETED,
    ADMIN_SERVICE_INACTIVE,
    ADMIN_SERVICE_INVALID_PRICE,
    ADMIN_SERVICE_ITEM,
    ADMIN_SERVICE_NOT_FOUND,
    ADMIN_SERVICE_PROMPT_CATEGORY,
    ADMIN_SERVICE_PROMPT_DESCRIPTION,
    ADMIN_SERVICE_PROMPT_NAME,
    ADMIN_SERVICE_PROMPT_PRICE_FROM,
    ADMIN_SERVICE_PROMPT_PRICE_TO,
    ADMIN_SERVICE_UPDATED,
    ADMIN_SERVICES_HEADER,
    BTN_BACK,
    BTN_CANCEL,
    BTN_SKIP,
    FSM_CANCELLED,
    PRICE_FROM,
    PRICE_ON_REQUEST,
    PRICE_RANGE,
)

router = Router(name="admin_services")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def format_price(price_from: int | None, price_to: int | None) -> str:
    """Человекочитаемый диапазон цены."""
    if price_from is None and price_to is None:
        return PRICE_ON_REQUEST
    if price_from is not None and price_to is not None:
        return PRICE_RANGE.format(price_from=price_from, price_to=price_to)
    amount = price_from if price_from is not None else price_to
    return PRICE_FROM.format(price_from=amount)


def format_service_item(service: Service) -> str:
    """Строка услуги для админ-списка."""
    return ADMIN_SERVICE_ITEM.format(
        id=service.id,
        name=html.escape(service.name, quote=False),
        category=service.category.label(),
        price=format_price(service.price_from, service.price_to),
        active=ADMIN_SERVICE_ACTIVE if service.is_active else ADMIN_SERVICE_INACTIVE,
    )


def parse_optional_price(raw: str) -> tuple[bool, int | None]:
    """Разбирает цену: пусто, 0 и «Пропустить» → None; иначе неотрицательное целое."""
    text = raw.strip()
    if text in {"", "0", BTN_SKIP}:
        return True, None
    if text.isdigit():
        return True, int(text)
    return False, None


async def show_category_services(
    event: Message | CallbackQuery,
    session: AsyncSession,
    category: ServiceCategory,
) -> None:
    """Показывает услуги выбранной категории."""
    all_services = await ServiceRepo.list_all(session)
    services = [item for item in all_services if item.category is category]
    lines = [ADMIN_SERVICES_HEADER, category.label()]
    if services:
        lines.extend(format_service_item(item) for item in services)
    builder = InlineKeyboardBuilder.from_markup(services_list_kb(services))
    builder.row(
        InlineKeyboardButton(
            text=BTN_BACK,
            callback_data=NavCB(action="svc_cats").pack(),
        )
    )
    await show_screen(event, "\n".join(lines), builder.as_markup())


@router.callback_query(MenuCB.filter(F.action == "admin_services"))
@router.message(F.text == ADMIN_MENU_BUTTONS["services"])
async def services_root(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Корень раздела: список категорий."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.clear()
    await show_screen(event, ADMIN_SERVICE_PROMPT_CATEGORY, categories_admin_kb())


@router.callback_query(NavCB.filter(F.action == "svc_cats"))
async def services_categories_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат к списку категорий."""
    await callback.answer()
    await state.clear()
    await show_screen(callback, ADMIN_SERVICE_PROMPT_CATEGORY, categories_admin_kb())


@router.callback_query(ServiceAdminCB.filter(F.action == "cat"))
async def services_in_category(
    callback: CallbackQuery,
    callback_data: ServiceAdminCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Список услуг внутри категории."""
    await callback.answer()
    if callback.message is None:
        return
    try:
        category = ServiceCategory(callback_data.category)
    except ValueError:
        return
    current = await state.get_state()
    if current == AdminServiceStates.choose_category.state:
        await state.update_data(category=category.value)
        await state.set_state(AdminServiceStates.enter_name)
        await show_screen(callback, ADMIN_SERVICE_PROMPT_NAME, cancel_kb())
        return
    await show_category_services(callback, session, category)


@router.callback_query(ServiceAdminCB.filter(F.action == "add"))
async def service_add_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Запуск FSM добавления услуги."""
    await callback.answer()
    await state.set_state(AdminServiceStates.choose_category)
    await state.update_data(service_id=NEW_ITEM_ID)
    await show_screen(callback, ADMIN_SERVICE_PROMPT_CATEGORY, categories_admin_kb())


@router.callback_query(ServiceAdminCB.filter(F.action == "edit"))
async def service_edit_start(
    callback: CallbackQuery,
    callback_data: ServiceAdminCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Запуск FSM редактирования существующей услуги."""
    await callback.answer()
    service = await ServiceRepo.get_by_id(session, callback_data.service_id)
    if service is None:
        await show_screen(callback, ADMIN_SERVICE_NOT_FOUND)
        return
    await state.set_state(AdminServiceStates.choose_category)
    await state.update_data(
        service_id=service.id,
        category=service.category.value,
        name=service.name,
        description=service.description or "",
        price_from=service.price_from,
        price_to=service.price_to,
    )
    await show_screen(
        callback,
        f"{ADMIN_SERVICE_PROMPT_CATEGORY}\n{service.category.label()}",
        categories_admin_kb(),
    )


@router.callback_query(ServiceAdminCB.filter(F.action == "toggle"))
async def service_toggle(
    callback: CallbackQuery,
    callback_data: ServiceAdminCB,
    session: AsyncSession,
) -> None:
    """Скрывает или показывает услугу."""
    await callback.answer()
    service = await ServiceRepo.get_by_id(session, callback_data.service_id)
    if service is None:
        await show_screen(callback, ADMIN_SERVICE_NOT_FOUND)
        return
    service.is_active = not service.is_active
    await session.flush()
    await show_category_services(callback, session, service.category)


@router.callback_query(ServiceAdminCB.filter(F.action == "delete"))
async def service_delete(
    callback: CallbackQuery,
    callback_data: ServiceAdminCB,
    session: AsyncSession,
) -> None:
    """Удаляет услугу и обновляет список категории."""
    await callback.answer()
    try:
        category = ServiceCategory(callback_data.category)
    except ValueError:
        category = None
    deleted = await ServiceRepo.delete(session, callback_data.service_id)
    if not deleted:
        await show_screen(callback, ADMIN_SERVICE_NOT_FOUND)
        return
    if category is not None:
        await show_category_services(callback, session, category)
        return
    await show_admin_home(callback, session)


@router.callback_query(AdminServiceStates.choose_category, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminServiceStates.enter_name, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminServiceStates.enter_description, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminServiceStates.enter_price_from, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminServiceStates.enter_price_to, MenuCB.filter(F.action == "cancel"))
@router.callback_query(AdminServiceStates.confirm, MenuCB.filter(F.action == "cancel"))
@router.message(AdminServiceStates.choose_category, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_name, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_description, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_price_from, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_price_to, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.confirm, F.text == BTN_CANCEL)
async def service_fsm_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена любого шага FSM услуги."""
    message, _user = await ack_event(event)
    if message is None:
        return
    await state.clear()
    await show_admin_home(event, session)


@router.message(AdminServiceStates.enter_name, F.text)
async def service_enter_name(message: Message, state: FSMContext) -> None:
    """Название услуги."""
    name = (message.text or "").strip()
    if not name or name == BTN_CANCEL:
        await message.answer(ADMIN_SERVICE_PROMPT_NAME, reply_markup=cancel_kb())
        return
    await state.update_data(name=name)
    await state.set_state(AdminServiceStates.enter_description)
    await message.answer(ADMIN_SERVICE_PROMPT_DESCRIPTION, reply_markup=skip_cancel_kb())


@router.message(AdminServiceStates.enter_description, F.text)
async def service_enter_description(message: Message, state: FSMContext) -> None:
    """Описание услуги (можно пропустить)."""
    raw = (message.text or "").strip()
    description = None if raw in {"", BTN_SKIP} else raw
    await _save_service_description(message, state, description)


@router.callback_query(AdminServiceStates.enter_description, MenuCB.filter(F.action == "skip"))
async def service_skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропуск описания услуги."""
    await callback.answer()
    await _save_service_description(callback, state, None)


async def _save_service_description(
    event: Message | CallbackQuery,
    state: FSMContext,
    description: str | None,
) -> None:
    """Сохраняет описание и запрашивает цену «от»."""
    await state.update_data(description=description or "")
    await state.set_state(AdminServiceStates.enter_price_from)
    await show_screen(event, ADMIN_SERVICE_PROMPT_PRICE_FROM, skip_cancel_kb())


@router.message(AdminServiceStates.enter_price_from, F.text)
async def service_enter_price_from(message: Message, state: FSMContext) -> None:
    """Цена «от»."""
    await _save_price_from(message, state, message.text or "")


@router.callback_query(AdminServiceStates.enter_price_from, MenuCB.filter(F.action == "skip"))
async def service_skip_price_from(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропуск цены «от»."""
    await callback.answer()
    await _save_price_from(callback, state, BTN_SKIP)


async def _save_price_from(event: Message | CallbackQuery, state: FSMContext, raw: str) -> None:
    """Разбирает цену «от» и переходит к цене «до»."""
    ok, value = parse_optional_price(raw)
    if not ok:
        await show_screen(event, ADMIN_SERVICE_INVALID_PRICE, skip_cancel_kb())
        return
    await state.update_data(price_from=value)
    await state.set_state(AdminServiceStates.enter_price_to)
    await show_screen(event, ADMIN_SERVICE_PROMPT_PRICE_TO, skip_cancel_kb())


@router.message(AdminServiceStates.enter_price_to, F.text)
async def service_enter_price_to(message: Message, state: FSMContext) -> None:
    """Цена «до» и предпросмотр."""
    await _save_price_to(message, state, message.text or "")


@router.callback_query(AdminServiceStates.enter_price_to, MenuCB.filter(F.action == "skip"))
async def service_skip_price_to(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропуск цены «до»."""
    await callback.answer()
    await _save_price_to(callback, state, BTN_SKIP)


async def _save_price_to(event: Message | CallbackQuery, state: FSMContext, raw: str) -> None:
    """Разбирает цену «до» и показывает подтверждение."""
    ok, value = parse_optional_price(raw)
    if not ok:
        await show_screen(event, ADMIN_SERVICE_INVALID_PRICE, skip_cancel_kb())
        return
    await state.update_data(price_to=value)
    data = await state.get_data()
    category = ServiceCategory(str(data["category"]))
    preview = ADMIN_SERVICE_ITEM.format(
        id=int(data.get("service_id") or NEW_ITEM_ID),
        name=html.escape(str(data["name"]), quote=False),
        category=category.label(),
        price=format_price(data.get("price_from"), data.get("price_to")),
        active=ADMIN_SERVICE_ACTIVE,
    )
    description = str(data.get("description") or "").strip()
    if description:
        preview = f"{preview}\n{html.escape(description, quote=False)}"
    await state.set_state(AdminServiceStates.confirm)
    await show_screen(event, preview, confirm_kb())


@router.callback_query(AdminServiceStates.confirm, ConfirmCB.filter(F.action == "no"))
async def service_confirm_no(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отказ сохранить услугу."""
    await callback.answer()
    await state.clear()
    await show_admin_home(callback, session)


@router.callback_query(AdminServiceStates.confirm, ConfirmCB.filter(F.action == "yes"))
async def service_confirm_yes(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт или обновляет услугу."""
    await callback.answer()
    if callback.message is None:
        await state.clear()
        return
    data = await state.get_data()
    category = ServiceCategory(str(data["category"]))
    name = str(data["name"]).strip()
    description_raw = str(data.get("description") or "").strip()
    description = description_raw or None
    price_from = data.get("price_from")
    price_to = data.get("price_to")
    service_id = int(data.get("service_id") or NEW_ITEM_ID)
    await state.clear()

    if service_id == NEW_ITEM_ID:
        service = await ServiceRepo.create(
            session,
            category=category,
            name=name,
            description=description,
            price_from=price_from if isinstance(price_from, int) else None,
            price_to=price_to if isinstance(price_to, int) else None,
        )
        text = ADMIN_SERVICE_CREATED.format(name=service.name)
    else:
        service = await ServiceRepo.update(
            session,
            service_id,
            category=category,
            name=name,
            description=description,
            price_from=price_from if isinstance(price_from, int) else None,
            price_to=price_to if isinstance(price_to, int) else None,
        )
        if service is None:
            await show_screen(callback, ADMIN_SERVICE_NOT_FOUND)
            await show_admin_home(callback, session)
            return
        text = ADMIN_SERVICE_UPDATED.format(name=service.name)

    await show_screen(callback, text)
    await show_admin_home(callback, session)
