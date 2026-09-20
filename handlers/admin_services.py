"""Админ: управление услугами прайса."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Service, ServiceCategory
from database.repo import ServiceRepo
from filters.admin import IsAdmin
from keyboards.reply import (
    admin_menu_kb,
    cancel_kb,
    category_from_label,
    confirm_kb,
    list_kb,
    numbered_label,
    parse_numbered,
    service_categories_kb,
    service_item_kb,
    skip_cancel_kb,
)
from states.admin import AdminPickStates, AdminServiceStates
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
    BTN_ADD,
    BTN_BACK,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_DELETE,
    BTN_EDIT,
    BTN_SKIP,
    BTN_TOGGLE,
    FSM_CANCELLED,
    PRICE_FROM,
    PRICE_ON_REQUEST,
    PRICE_RANGE,
)

_CAT_LABELS = {item.label() for item in ServiceCategory}

router = Router(name="admin_services")
router.message.filter(IsAdmin())

NEW_ITEM_ID = 0


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
    """Разбирает цену: пусто, 0 и «Пропустить» → None."""
    text = raw.strip()
    if text in {"", "0", BTN_SKIP}:
        return True, None
    if text.isdigit():
        return True, int(text)
    return False, None


async def show_categories(message: Message, state: FSMContext) -> None:
    """Корень: категории."""
    await state.set_state(AdminPickStates.service_cats)
    await message.answer(ADMIN_SERVICE_PROMPT_CATEGORY, reply_markup=service_categories_kb(with_cancel=False))


async def show_category_services(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    category: ServiceCategory,
) -> None:
    """Услуги выбранной категории."""
    all_services = await ServiceRepo.list_all(session)
    services = [item for item in all_services if item.category is category]
    await state.set_state(AdminPickStates.services)
    await state.update_data(browse_category=category.value)
    lines = [ADMIN_SERVICES_HEADER, category.label()]
    if services:
        lines.extend(format_service_item(item) for item in services)
    labels = [numbered_label(item.id, item.name) for item in services]
    await message.answer(
        "\n".join(lines),
        reply_markup=list_kb(labels, extra=[BTN_ADD]),
    )


@router.message(F.text == ADMIN_MENU_BUTTONS["services"])
async def services_root(message: Message, state: FSMContext) -> None:
    """Корень раздела: список категорий."""
    await state.clear()
    await show_categories(message, state)


@router.message(AdminPickStates.service_cats, F.text == BTN_BACK)
@router.message(AdminPickStates.service_cats, F.text == BTN_CANCEL)
async def services_cats_back(message: Message, state: FSMContext) -> None:
    """Назад в админ-меню."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminPickStates.service_cats, F.text.in_(_CAT_LABELS))
async def services_pick_cat(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Категория при просмотре."""
    category = category_from_label(message.text or "")
    if category is None:
        return
    await show_category_services(message, state, session, category)


@router.message(AdminPickStates.services, F.text == BTN_BACK)
async def services_list_back(message: Message, state: FSMContext) -> None:
    """Из списка услуг к категориям."""
    await show_categories(message, state)


@router.message(AdminPickStates.services, F.text == BTN_ADD)
async def service_add_start(message: Message, state: FSMContext) -> None:
    """FSM добавления услуги."""
    await state.set_state(AdminServiceStates.choose_category)
    await state.update_data(service_id=NEW_ITEM_ID)
    await message.answer(ADMIN_SERVICE_PROMPT_CATEGORY, reply_markup=service_categories_kb())


@router.message(AdminPickStates.services, F.text.regexp(r"^№\d+"))
async def services_pick_item(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Открывает карточку услуги."""
    service_id = parse_numbered(message.text or "")
    if service_id is None:
        return
    service = await ServiceRepo.get_by_id(session, service_id)
    if service is None:
        await message.answer(ADMIN_SERVICE_NOT_FOUND, reply_markup=admin_menu_kb())
        await state.clear()
        return
    await state.set_state(AdminPickStates.service_item)
    await state.update_data(service_id=service.id, browse_category=service.category.value)
    await message.answer(format_service_item(service), reply_markup=service_item_kb())


@router.message(AdminPickStates.service_item, F.text == BTN_BACK)
async def service_item_back(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Назад к списку категории."""
    data = await state.get_data()
    category = ServiceCategory(str(data["browse_category"]))
    await show_category_services(message, state, session, category)


@router.message(AdminPickStates.service_item, F.text == BTN_EDIT)
async def service_edit_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """FSM редактирования."""
    data = await state.get_data()
    service = await ServiceRepo.get_by_id(session, int(data["service_id"]))
    if service is None:
        await state.clear()
        await message.answer(ADMIN_SERVICE_NOT_FOUND, reply_markup=admin_menu_kb())
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
    await message.answer(
        f"{ADMIN_SERVICE_PROMPT_CATEGORY}\n{service.category.label()}",
        reply_markup=service_categories_kb(),
    )


@router.message(AdminPickStates.service_item, F.text == BTN_TOGGLE)
async def service_toggle(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Скрывает или показывает услугу."""
    data = await state.get_data()
    service = await ServiceRepo.get_by_id(session, int(data["service_id"]))
    if service is None:
        await state.clear()
        await message.answer(ADMIN_SERVICE_NOT_FOUND, reply_markup=admin_menu_kb())
        return
    service.is_active = not service.is_active
    await session.flush()
    await message.answer(format_service_item(service), reply_markup=service_item_kb())


@router.message(AdminPickStates.service_item, F.text == BTN_DELETE)
async def service_delete(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Удаляет услугу."""
    data = await state.get_data()
    service_id = int(data["service_id"])
    category = ServiceCategory(str(data["browse_category"]))
    deleted = await ServiceRepo.delete(session, service_id)
    if not deleted:
        await state.clear()
        await message.answer(ADMIN_SERVICE_NOT_FOUND, reply_markup=admin_menu_kb())
        return
    await message.answer(ADMIN_SERVICE_DELETED)
    await show_category_services(message, state, session, category)


@router.message(AdminServiceStates.choose_category, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_name, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_description, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_price_from, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.enter_price_to, F.text == BTN_CANCEL)
@router.message(AdminServiceStates.confirm, F.text == BTN_CANCEL)
async def service_fsm_cancel(message: Message, state: FSMContext) -> None:
    """Отмена FSM услуги."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminServiceStates.choose_category, F.text)
async def service_fsm_category(message: Message, state: FSMContext) -> None:
    """Категория на шаге создания/редактирования."""
    category = category_from_label(message.text or "")
    if category is None:
        await message.answer(ADMIN_SERVICE_PROMPT_CATEGORY, reply_markup=service_categories_kb())
        return
    await state.update_data(category=category.value)
    await state.set_state(AdminServiceStates.enter_name)
    await message.answer(ADMIN_SERVICE_PROMPT_NAME, reply_markup=cancel_kb())


@router.message(AdminServiceStates.enter_name, F.text)
async def service_enter_name(message: Message, state: FSMContext) -> None:
    """Название услуги."""
    name = (message.text or "").strip()
    if not name:
        await message.answer(ADMIN_SERVICE_PROMPT_NAME, reply_markup=cancel_kb())
        return
    await state.update_data(name=name)
    await state.set_state(AdminServiceStates.enter_description)
    await message.answer(ADMIN_SERVICE_PROMPT_DESCRIPTION, reply_markup=skip_cancel_kb())


@router.message(AdminServiceStates.enter_description, F.text)
async def service_enter_description(message: Message, state: FSMContext) -> None:
    """Описание услуги."""
    raw = (message.text or "").strip()
    description = None if raw in {"", BTN_SKIP} else raw
    await state.update_data(description=description or "")
    await state.set_state(AdminServiceStates.enter_price_from)
    await message.answer(ADMIN_SERVICE_PROMPT_PRICE_FROM, reply_markup=skip_cancel_kb())


@router.message(AdminServiceStates.enter_price_from, F.text)
async def service_enter_price_from(message: Message, state: FSMContext) -> None:
    """Цена «от»."""
    ok, value = parse_optional_price(message.text or "")
    if not ok:
        await message.answer(ADMIN_SERVICE_INVALID_PRICE, reply_markup=skip_cancel_kb())
        return
    await state.update_data(price_from=value)
    await state.set_state(AdminServiceStates.enter_price_to)
    await message.answer(ADMIN_SERVICE_PROMPT_PRICE_TO, reply_markup=skip_cancel_kb())


@router.message(AdminServiceStates.enter_price_to, F.text)
async def service_enter_price_to(message: Message, state: FSMContext) -> None:
    """Цена «до» и предпросмотр."""
    ok, value = parse_optional_price(message.text or "")
    if not ok:
        await message.answer(ADMIN_SERVICE_INVALID_PRICE, reply_markup=skip_cancel_kb())
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
    await message.answer(preview, reply_markup=confirm_kb())


@router.message(AdminServiceStates.confirm, F.text == BTN_CONFIRM)
async def service_confirm_yes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт или обновляет услугу."""
    data = await state.get_data()
    category = ServiceCategory(str(data["category"]))
    name = str(data["name"]).strip()
    description_raw = str(data.get("description") or "").strip()
    description = description_raw or None
    price_from = data.get("price_from")
    price_to = data.get("price_to")
    service_id = int(data.get("service_id") or NEW_ITEM_ID)

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
            await state.clear()
            await message.answer(ADMIN_SERVICE_NOT_FOUND, reply_markup=admin_menu_kb())
            return
        text = ADMIN_SERVICE_UPDATED.format(name=service.name)

    await message.answer(text)
    await show_category_services(message, state, session, category)
