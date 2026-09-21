"""Mini App (web_app_data) и быстрая запись в чате."""

from __future__ import annotations

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestSource, RequestType, User
from database.repo import RequestRepo, UserRepo
from handlers.start import (
    ack_event,
    answer_with_menu,
    get_or_create_user,
    require_client,
    show_screen,
)
from keyboards.inline import (
    MenuCB,
    admin_request_actions_kb,
    cancel_kb,
    skip_cancel_kb,
)
from keyboards.reply import phone_request_kb
from services.notify import notify_admins
from states.client import QuickBookingStates
from texts import (
    BTN_CANCEL,
    ERROR_PHONE_INVALID,
    MINIAPP_BAD_DATA,
    MINIAPP_CREATED,
    QUICK_CREATED,
    QUICK_NOTE_PROMPT,
    QUICK_NOTE_SKIPPED,
    QUICK_PHONE_PROMPT,
    ADMIN_MINIAPP_NOTIFY,
    ADMIN_QUICK_NOTIFY,
    MENU_BUTTONS,
)
from utils.validators import format_phone_display, normalize_phone

logger = logging.getLogger(__name__)

router = Router(name="booking")


def _username(user: User) -> str:
    """@username или «без ника»."""
    return f"@{user.username}" if user.username else "—"


def _services_block(services_text: str | None) -> str:
    """Маркированный список услуг."""
    raw = (services_text or "").strip()
    if not raw:
        return "   • не указаны"
    lines = []
    for part in raw.replace(";", "\n").split("\n"):
        item = part.strip(" •-\t")
        if item:
            lines.append(f"   • {item}")
    return "\n".join(lines) if lines else "   • не указаны"


def format_miniapp_card(request_id: int, user: User, *, car: str, services: str, slot: str, comment: str) -> str:
    """Карточка записи из Mini App для админов."""
    return ADMIN_MINIAPP_NOTIFY.format(
        request_id=request_id,
        name=user.full_name,
        username=_username(user),
        phone=format_phone_display(user.phone) or "не указан",
        car=car or "не указано",
        services=_services_block(services),
        slot=slot or "не указана",
        comment=comment or "—",
    )


def format_quick_card(request_id: int, user: User, note: str) -> str:
    """Карточка срочного звонка."""
    return ADMIN_QUICK_NOTIFY.format(
        request_id=request_id,
        name=user.full_name,
        username=_username(user),
        phone=format_phone_display(user.phone) or "не указан",
        note=note or QUICK_NOTE_SKIPPED,
    )


def _parse_webapp_payload(raw: str) -> dict[str, str]:
    """Разбирает JSON из Mini App."""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("payload is not an object")
    services = data.get("services")
    if isinstance(services, list):
        services_text = "\n".join(str(item).strip() for item in services if str(item).strip())
    else:
        services_text = str(services or "").strip()
    car = str(data.get("car") or data.get("auto") or "").strip()
    plate = str(data.get("plate") or data.get("gosnomer") or "").strip()
    if plate:
        car = f"{car} ({plate})".strip()
    return {
        "phone": str(data.get("phone") or "").strip(),
        "car": car,
        "services": services_text,
        "slot": str(data.get("datetime") or data.get("slot") or data.get("date") or "").strip(),
        "comment": str(data.get("comment") or data.get("note") or "").strip(),
    }


@router.message(F.web_app_data)
async def webapp_booking(
    message: Message,
    session: AsyncSession,
) -> None:
    """Принимает заявку из Mini App."""
    if message.from_user is None or message.web_app_data is None:
        return
    user, _created = await get_or_create_user(session, message.from_user)
    if user.is_blocked:
        return
    try:
        payload = _parse_webapp_payload(message.web_app_data.data)
    except (ValueError, json.JSONDecodeError):
        await message.answer(MINIAPP_BAD_DATA)
        return
    phone = normalize_phone(payload["phone"]) if payload["phone"] else None
    if phone:
        await UserRepo.update_phone(session, user.tg_id, phone)
        await session.refresh(user)
    comment = payload["comment"] or "Запись через Mini App"
    request = await RequestRepo.create(
        session,
        user_id=user.id,
        request_type=RequestType.BOOKING,
        text=comment,
        car_info=payload["car"] or None,
        source=RequestSource.MINIAPP,
        desired_slot=payload["slot"] or None,
        services_text=payload["services"] or None,
    )
    if message.bot is not None:
        await notify_admins(
            message.bot,
            session,
            format_miniapp_card(
                request.id,
                user,
                car=payload["car"],
                services=payload["services"],
                slot=payload["slot"],
                comment=comment,
            ),
            reply_markup=admin_request_actions_kb(
                request.id,
                slot=payload["slot"] or None,
                phone=user.phone,
                source=RequestSource.MINIAPP.value,
            ),
        )
    await message.answer(
        MINIAPP_CREATED.format(request_id=request.id),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.callback_query(MenuCB.filter(F.action == "quick"))
@router.message(F.text == MENU_BUTTONS["quick"])
async def quick_entry(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Старт экспресс-записи."""
    message, tg_user = await ack_event(event)
    if message is None or tg_user is None:
        return
    user = await require_client(event, session, tg_user)
    if user is None:
        return
    await state.clear()
    if not user.phone:
        await state.set_state(QuickBookingStates.enter_phone)
        await show_screen(event, QUICK_PHONE_PROMPT, cancel_kb())
        await message.answer("👇", reply_markup=phone_request_kb())
        return
    await state.set_state(QuickBookingStates.enter_note)
    await show_screen(event, QUICK_NOTE_PROMPT, skip_cancel_kb())


@router.message(QuickBookingStates.enter_phone, F.contact)
async def quick_phone_contact(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Сохраняет контакт с reply-кнопки."""
    if message.from_user is None or message.contact is None:
        return
    if message.contact.user_id not in (None, 0, message.from_user.id):
        await message.answer(ERROR_PHONE_INVALID, reply_markup=phone_request_kb())
        return
    phone = normalize_phone(message.contact.phone_number)
    if phone is None:
        await message.answer(ERROR_PHONE_INVALID, reply_markup=phone_request_kb())
        return
    await _save_phone_and_ask_note(message, session, state, phone)


@router.message(QuickBookingStates.enter_phone, F.text)
async def quick_phone_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Принимает номер текстом."""
    if (message.text or "").strip() == BTN_CANCEL:
        return
    phone = normalize_phone(message.text or "")
    if phone is None:
        await message.answer(ERROR_PHONE_INVALID, reply_markup=phone_request_kb())
        return
    await _save_phone_and_ask_note(message, session, state, phone)


async def _save_phone_and_ask_note(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    phone: str,
) -> None:
    """Пишет телефон и переходит к необязательному комментарию."""
    if message.from_user is None:
        return
    user, _created = await get_or_create_user(session, message.from_user)
    await UserRepo.update_phone(session, user.tg_id, phone)
    await message.answer("\u2060", reply_markup=ReplyKeyboardRemove())
    await state.set_state(QuickBookingStates.enter_note)
    await message.answer(QUICK_NOTE_PROMPT, reply_markup=skip_cancel_kb())


@router.callback_query(QuickBookingStates.enter_phone, MenuCB.filter(F.action == "cancel"))
@router.callback_query(QuickBookingStates.enter_note, MenuCB.filter(F.action == "cancel"))
@router.message(QuickBookingStates.enter_phone, F.text == BTN_CANCEL)
@router.message(QuickBookingStates.enter_note, F.text == BTN_CANCEL)
async def quick_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена быстрой записи."""
    message, tg_user = await ack_event(event)
    if message is None or tg_user is None:
        return
    await state.clear()
    user, _created = await get_or_create_user(session, tg_user)
    if isinstance(event, Message):
        await event.answer("\u2060", reply_markup=ReplyKeyboardRemove())
    await answer_with_menu(event, user, "↩️ Запрос на звонок отменён.")


@router.callback_query(QuickBookingStates.enter_note, MenuCB.filter(F.action == "skip"))
async def quick_skip_note(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Пропуск комментария."""
    await callback.answer()
    await _finish_quick(callback, session, state, QUICK_NOTE_SKIPPED)


@router.message(QuickBookingStates.enter_note, F.text)
async def quick_note_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сохраняет пожелание и создаёт заявку."""
    note = (message.text or "").strip()
    if not note or note == BTN_CANCEL:
        return
    await _finish_quick(message, session, state, note)


async def _finish_quick(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    note: str,
) -> None:
    """Создаёт заявку на звонок и уведомляет админов."""
    from handlers.start import unpack_event

    message, tg_user = unpack_event(event)
    if message is None or tg_user is None:
        return
    user = await require_client(event, session, tg_user)
    if user is None:
        await state.clear()
        return
    request = await RequestRepo.create(
        session,
        user_id=user.id,
        request_type=RequestType.BOOKING,
        text=note,
        car_info=None if note == QUICK_NOTE_SKIPPED else note[:255],
        source=RequestSource.QUICK,
    )
    await state.clear()
    if message.bot is not None:
        await notify_admins(
            message.bot,
            session,
            format_quick_card(request.id, user, note),
            reply_markup=admin_request_actions_kb(
                request.id,
                phone=user.phone,
                source=RequestSource.QUICK.value,
            ),
        )
    await answer_with_menu(event, user, QUICK_CREATED)
