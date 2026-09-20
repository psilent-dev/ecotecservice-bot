"""FSM запроса ориентировочной стоимости."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestType, ServiceCategory
from database.repo import RequestRepo
from handlers.booking import cancel_client_fsm, notify_admins_new_request
from handlers.start import answer_with_menu, require_client
from keyboards.reply import cancel_kb, category_from_label, confirm_kb, service_categories_kb
from states.client import PriceStates
from texts import (
    BOOKING_INVALID_SERVICE,
    BTN_CANCEL,
    BTN_CONFIRM,
    MENU_BUTTONS,
    PRICE_CANCELLED,
    PRICE_CAR_INFO,
    PRICE_CHOOSE_SERVICE,
    PRICE_CONFIRM,
    PRICE_CREATED,
    PRICE_ON_REQUEST,
)

router = Router(name="price_request")


@router.message(F.text == MENU_BUTTONS["price"])
async def price_entry(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Старт запроса цены: выбор категории."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        return
    await state.clear()
    await state.set_state(PriceStates.choose_service)
    await message.answer(PRICE_CHOOSE_SERVICE, reply_markup=service_categories_kb())


@router.message(PriceStates.choose_service, F.text == BTN_CANCEL)
@router.message(PriceStates.enter_car, F.text == BTN_CANCEL)
@router.message(PriceStates.confirm, F.text == BTN_CANCEL)
async def price_cancel_button(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Выход из запроса цены."""
    await cancel_client_fsm(message, state, session, PRICE_CANCELLED)


@router.message(PriceStates.choose_service, F.text)
async def price_choose_service(message: Message, state: FSMContext) -> None:
    """Сохраняет категорию и запрашивает автомобиль."""
    category = category_from_label(message.text or "")
    if category is None:
        await message.answer(BOOKING_INVALID_SERVICE, reply_markup=service_categories_kb())
        return
    await state.update_data(service=category.value)
    await state.set_state(PriceStates.enter_car)
    await message.answer(PRICE_CAR_INFO, reply_markup=cancel_kb())


@router.message(PriceStates.enter_car, F.text)
async def price_enter_car(message: Message, state: FSMContext) -> None:
    """Сохраняет автомобиль и показывает сводку."""
    car_info = (message.text or "").strip()
    if not car_info:
        await message.answer(PRICE_CAR_INFO, reply_markup=cancel_kb())
        return
    await state.update_data(car_info=car_info)
    data = await state.get_data()
    try:
        category = ServiceCategory(data["service"])
    except (KeyError, ValueError):
        await state.set_state(PriceStates.choose_service)
        await message.answer(BOOKING_INVALID_SERVICE, reply_markup=service_categories_kb())
        return
    await state.set_state(PriceStates.confirm)
    await message.answer(
        PRICE_CONFIRM.format(service=category.label(), car=car_info),
        reply_markup=confirm_kb(),
    )


@router.message(PriceStates.confirm, F.text == BTN_CONFIRM)
async def price_confirm_yes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт заявку PRICE и уведомляет администраторов."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    try:
        category = ServiceCategory(data["service"])
    except (KeyError, ValueError):
        await state.set_state(PriceStates.choose_service)
        await message.answer(BOOKING_INVALID_SERVICE, reply_markup=service_categories_kb())
        return
    car_info = str(data.get("car_info", "")).strip()
    request = await RequestRepo.create(
        session,
        user_id=user.id,
        request_type=RequestType.PRICE,
        text=PRICE_ON_REQUEST,
        service=category,
        car_info=car_info,
    )
    await notify_admins_new_request(
        message,
        session,
        request_id=request.id,
        request_type=RequestType.PRICE,
        user=user,
        service=category,
        car_info=car_info,
        text=PRICE_ON_REQUEST,
    )
    await state.clear()
    await answer_with_menu(
        message,
        user,
        PRICE_CREATED.format(request_id=request.id),
    )


@router.message(PriceStates.confirm, F.text)
async def price_confirm_hint(message: Message) -> None:
    """Напоминает подтвердить кнопками."""
    await message.answer(PRICE_CONFIRM.format(service="—", car="—"), reply_markup=confirm_kb())
