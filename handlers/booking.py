"""FSM записи на обслуживание."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestType, ServiceCategory, User
from database.repo import RequestRepo, UserRepo
from handlers.start import answer_with_menu, require_client, safe_send
from keyboards.inline import ConfirmCB, ServiceCB, admin_request_actions_kb, confirm_kb, service_categories_kb
from keyboards.reply import cancel_kb
from states.client import BookingStates
from texts import (
    ADMIN_NEW_REQUEST,
    ADMIN_REQUEST_NO_CAR,
    ADMIN_REQUEST_NO_SERVICE,
    BOOKING_CANCELLED,
    BOOKING_CAR_INFO,
    BOOKING_CHOOSE_SERVICE,
    BOOKING_COMMENT,
    BOOKING_CONFIRM,
    BOOKING_CREATED,
    BOOKING_EMPTY_TEXT,
    BOOKING_INVALID_SERVICE,
    BTN_CANCEL,
    DISCOUNT_LINE_FREE_DIAG,
    DISCOUNT_LINE_LOYALTY,
    DISCOUNT_LINE_REFERRAL,
    MENU_BUTTONS,
    PROFILE_NO_PHONE,
    REQUEST_TYPE_LABELS,
)

logger = logging.getLogger(__name__)

router = Router(name="booking")


def loyalty_annotations(user: User, category: ServiceCategory) -> str:
    """Строки лояльности, которые уходят в заявку и админам."""
    lines: list[str] = []
    if user.loyalty_discount_2nd:
        lines.append(DISCOUNT_LINE_LOYALTY)
    if user.discount_10_active:
        lines.append(DISCOUNT_LINE_REFERRAL)
    if user.free_diagnostics and category is ServiceCategory.DIAGNOSTICS:
        lines.append(DISCOUNT_LINE_FREE_DIAG)
    return "\n".join(lines)


async def consume_booking_loyalty(
    session: AsyncSession,
    user: User,
    category: ServiceCategory,
) -> None:
    """Сжигает использованные флаги скидок при подтверждении записи."""
    if user.free_diagnostics and category is ServiceCategory.DIAGNOSTICS:
        user.free_diagnostics = False
    if user.discount_10_active:
        user.discount_10_active = False
    if user.loyalty_discount_2nd:
        user.visits_count += 1
        user.loyalty_discount_2nd = False
    await session.flush()


def format_admin_request_card(
    *,
    request_id: int,
    request_type: RequestType,
    user: User,
    service: ServiceCategory | None,
    car_info: str | None,
    text: str,
) -> str:
    """Карточка заявки для лички администратора."""
    username = user.username or ADMIN_REQUEST_NO_CAR
    discounts = loyalty_annotations(user, service) if service is not None else ""
    return ADMIN_NEW_REQUEST.format(
        request_id=request_id,
        type=REQUEST_TYPE_LABELS[request_type.value],
        service=service.label() if service is not None else ADMIN_REQUEST_NO_SERVICE,
        car=car_info or ADMIN_REQUEST_NO_CAR,
        name=user.full_name,
        username=username,
        phone=user.phone or PROFILE_NO_PHONE,
        text=text,
        discounts=discounts,
    )


async def notify_admins_new_request(
    message: Message,
    session: AsyncSession,
    *,
    request_id: int,
    request_type: RequestType,
    user: User,
    service: ServiceCategory | None,
    car_info: str | None,
    text: str,
) -> None:
    """Рассылает новую заявку всем администраторам, ошибки доставки не прерывают сценарий."""
    if message.bot is None:
        logger.warning("Bot instance отсутствует, админы не уведомлены request_id=%s", request_id)
        return
    card = format_admin_request_card(
        request_id=request_id,
        request_type=request_type,
        user=user,
        service=service,
        car_info=car_info,
        text=text,
    )
    markup = admin_request_actions_kb(request_id)
    admins = await UserRepo.get_all_admins(session)
    for admin in admins:
        await safe_send(
            message.bot,
            admin.tg_id,
            card,
            reply_markup=markup,
        )


async def cancel_client_fsm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    cancel_text: str,
    *,
    tg_id: int | None = None,
) -> None:
    """Сбрасывает FSM и возвращает в меню."""
    await state.clear()
    lookup_id = tg_id
    if lookup_id is None and message.from_user is not None:
        lookup_id = message.from_user.id
    if lookup_id is None:
        await message.answer(cancel_text)
        return
    user = await UserRepo.get_by_tg_id(session, lookup_id)
    if user is None:
        await message.answer(cancel_text)
        return
    await answer_with_menu(message, user, cancel_text)


@router.message(F.text == MENU_BUTTONS["booking"])
async def booking_entry(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Старт записи: выбор категории услуги."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        return
    await state.clear()
    await state.set_state(BookingStates.choose_service)
    await message.answer(BOOKING_CHOOSE_SERVICE, reply_markup=cancel_kb())
    await message.answer(BOOKING_CHOOSE_SERVICE, reply_markup=service_categories_kb())


@router.callback_query(BookingStates.choose_service, ServiceCB.filter(F.action == "choose"))
async def booking_choose_service(
    callback: CallbackQuery,
    callback_data: ServiceCB,
    state: FSMContext,
) -> None:
    """Сохраняет категорию и запрашивает описание проблемы."""
    await callback.answer()
    try:
        category = ServiceCategory(callback_data.value)
    except ValueError:
        if callback.message:
            await callback.message.answer(BOOKING_INVALID_SERVICE)
        return
    await state.update_data(service=category.value)
    await state.set_state(BookingStates.enter_problem)
    if callback.message:
        await callback.message.answer(BOOKING_COMMENT, reply_markup=cancel_kb())


@router.message(BookingStates.enter_problem, F.text == BTN_CANCEL)
@router.message(BookingStates.enter_car, F.text == BTN_CANCEL)
@router.message(BookingStates.choose_service, F.text == BTN_CANCEL)
@router.message(BookingStates.confirm, F.text == BTN_CANCEL)
async def booking_cancel_button(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Выход из записи по reply-кнопке отмены."""
    await cancel_client_fsm(message, state, session, BOOKING_CANCELLED)


@router.message(BookingStates.enter_problem, F.text)
async def booking_enter_problem(
    message: Message,
    state: FSMContext,
) -> None:
    """Сохраняет описание работ."""
    problem = (message.text or "").strip()
    if not problem:
        await message.answer(BOOKING_EMPTY_TEXT, reply_markup=cancel_kb())
        return
    await state.update_data(problem=problem)
    await state.set_state(BookingStates.enter_car)
    await message.answer(BOOKING_CAR_INFO, reply_markup=cancel_kb())


@router.message(BookingStates.enter_car, F.text)
async def booking_enter_car(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сохраняет данные автомобиля и показывает сводку."""
    if message.from_user is None:
        return
    car_info = (message.text or "").strip()
    if not car_info:
        await message.answer(BOOKING_CAR_INFO, reply_markup=cancel_kb())
        return
    await state.update_data(car_info=car_info)
    data = await state.get_data()
    try:
        category = ServiceCategory(data["service"])
    except (KeyError, ValueError):
        await state.set_state(BookingStates.choose_service)
        await message.answer(BOOKING_INVALID_SERVICE, reply_markup=service_categories_kb())
        return
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    notes = loyalty_annotations(user, category) if user is not None else ""
    await state.set_state(BookingStates.confirm)
    await message.answer(
        BOOKING_CONFIRM.format(
            service=category.label(),
            car=car_info,
            problem=data.get("problem", ""),
            discounts=notes,
        ),
        reply_markup=confirm_kb(),
    )


@router.callback_query(BookingStates.confirm, ConfirmCB.filter(F.action == "no"))
async def booking_confirm_no(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена записи с inline-кнопки."""
    await callback.answer()
    if callback.message:
        await cancel_client_fsm(
            callback.message,
            state,
            session,
            BOOKING_CANCELLED,
            tg_id=callback.from_user.id if callback.from_user else None,
        )


@router.callback_query(BookingStates.confirm, ConfirmCB.filter(F.action == "yes"))
async def booking_confirm_yes(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт заявку, уведомляет админов и применяет скидки."""
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return
    user = await require_client(callback.message, session, callback.from_user)
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    try:
        category = ServiceCategory(data["service"])
    except (KeyError, ValueError):
        await state.set_state(BookingStates.choose_service)
        await callback.message.answer(BOOKING_INVALID_SERVICE, reply_markup=service_categories_kb())
        return
    problem = str(data.get("problem", "")).strip()
    car_info = str(data.get("car_info", "")).strip()
    notes = loyalty_annotations(user, category)
    request_text = problem if not notes else f"{problem}\n\n{notes}"
    request = await RequestRepo.create(
        session,
        user_id=user.id,
        request_type=RequestType.BOOKING,
        text=request_text,
        service=category,
        car_info=car_info,
    )
    await consume_booking_loyalty(session, user, category)
    await notify_admins_new_request(
        callback.message,
        session,
        request_id=request.id,
        request_type=RequestType.BOOKING,
        user=user,
        service=category,
        car_info=car_info,
        text=request_text,
    )
    await state.clear()
    await answer_with_menu(
        callback.message,
        user,
        BOOKING_CREATED.format(request_id=request.id),
    )
