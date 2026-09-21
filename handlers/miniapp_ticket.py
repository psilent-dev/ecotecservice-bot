"""Чек-тикет Mini App: вопрос мастерам и отмена / перенос записи."""

from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ClientRequest, RequestSource, RequestStatus, RequestType, User
from database.repo import RequestRepo
from handlers.start import ack_event, get_or_create_user, show_screen
from keyboards.inline import (
    MenuCB,
    admin_request_actions_kb,
    cancel_kb,
    main_menu_kb,
)
from services.notify import notify_admins
from states.client import MiniAppTicketStates
from texts import (
    BOOKING_REVOKE_NO_ACTIVE,
    BOOKING_REVOKE_TOAST,
    BOOKING_REVOKED_ADMIN,
    BOOKING_REVOKED_CLIENT,
    BTN_CANCEL,
    CONTACT_MASTER_ADMIN,
    CONTACT_MASTER_PROMPT,
    CONTACT_MASTER_SENT,
    FSM_CANCELLED,
    QUESTION_EMPTY,
)
from utils.validators import format_phone_display

router = Router(name="miniapp_ticket")

_CANCEL_PREFIXES = (
    "cancel_booking_",
    "cancel_record_",
    "revoke_booking_",
    "move_booking_",
    "reschedule_",
    "postpone_",
    "cancel_",
)
_RESCHEDULE_PREFIXES = ("reschedule_", "postpone_", "move_booking_")
_CONTACT_PREFIX = "contact_master_"


class TicketCancelFilter(Filter):
    """Кнопки отмены и переноса записи с чек-тикета Mini App."""

    async def __call__(self, event: TelegramObject) -> bool | dict[str, str]:
        """Разбирает callback_data и возвращает номер заявки и тип действия."""
        if not isinstance(event, CallbackQuery) or not event.data:
            return False
        data = event.data
        for prefix in _CANCEL_PREFIXES:
            if data.startswith(prefix):
                ref = data[len(prefix) :].strip()
                if not ref:
                    return False
                action = (
                    "перенос"
                    if any(data.startswith(item) for item in _RESCHEDULE_PREFIXES)
                    else "отмена"
                )
                return {"ticket_ref": ref, "ticket_action": action}
        return False


def _esc(value: str) -> str:
    """Экранирует пользовательский текст для HTML."""
    return html.escape(value, quote=False)


def _username(user: User) -> str:
    """@username или тире."""
    return f"@{user.username}" if user.username else "—"


def _as_int_id(raw: str) -> int | None:
    """Целочисленный номер заявки, если сайт передал цифры."""
    if re.fullmatch(r"\d+", raw):
        return int(raw)
    return None


async def _local_request(session: AsyncSession, user: User, ticket_ref: str) -> ClientRequest | None:
    """Локальная заявка клиента, если номер совпал с записью в боте."""
    request_id = _as_int_id(ticket_ref)
    if request_id is None:
        return None
    request = await RequestRepo.get_by_id(session, request_id)
    if request is None or request.user_id != user.id:
        return None
    return request


async def _latest_active_miniapp(session: AsyncSession, user: User) -> ClientRequest | None:
    """Последняя незакрытая запись Mini App этого клиента."""
    items = await RequestRepo.get_user_requests(session, user.id, limit=30)
    for request in items:
        if request.source is RequestSource.MINIAPP and request.status != RequestStatus.CLOSED:
            return request
    return None


def _contact_card(user: User) -> dict[str, str]:
    """Поля контакта клиента для уведомления админам."""
    return {
        "name": _esc(user.full_name),
        "username": _esc(_username(user)),
        "phone": format_phone_display(user.phone) or "не указан",
        "tg_id": str(user.tg_id),
    }


async def _revoke(
    event: Message | CallbackQuery,
    session: AsyncSession,
    user: User,
    ticket_ref: str,
    action: str,
) -> None:
    """Закрывает локальную заявку, если есть, и уведомляет администраторов."""
    request = await _local_request(session, user, ticket_ref)
    if request is not None and request.status != RequestStatus.CLOSED:
        await RequestRepo.update_status(session, request.id, RequestStatus.CLOSED)
    bot = event.bot
    if bot is not None:
        await notify_admins(
            bot,
            session,
            BOOKING_REVOKED_ADMIN.format(id=ticket_ref, action=action, **_contact_card(user)),
        )
    text = BOOKING_REVOKED_CLIENT.format(id=ticket_ref)
    if isinstance(event, CallbackQuery):
        await event.answer(BOOKING_REVOKE_TOAST, show_alert=True)
    await show_screen(event, text, main_menu_kb())


@router.callback_query(F.data.startswith(_CONTACT_PREFIX))
async def contact_master_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Старт быстрого диалога с мастерами по заявке из чек-тикета."""
    if callback.from_user is None or not callback.data:
        return
    user, _created = await get_or_create_user(session, callback.from_user)
    if user.is_blocked:
        await callback.answer()
        return
    ticket_ref = callback.data[len(_CONTACT_PREFIX) :].strip()
    if not ticket_ref:
        await callback.answer()
        return
    await callback.answer()
    await state.set_state(MiniAppTicketStates.contact_master)
    await state.update_data(ticket_ref=ticket_ref)
    if callback.message is not None:
        await callback.message.answer(
            CONTACT_MASTER_PROMPT.format(id=ticket_ref),
            reply_markup=cancel_kb(),
        )


@router.callback_query(MiniAppTicketStates.contact_master, MenuCB.filter(F.action == "cancel"))
@router.message(MiniAppTicketStates.contact_master, F.text == BTN_CANCEL)
async def contact_master_cancel(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Клиент передумал писать мастерам."""
    await ack_event(event)
    await state.clear()
    await show_screen(event, FSM_CANCELLED, main_menu_kb())


@router.message(MiniAppTicketStates.contact_master, F.text)
async def contact_master_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Пересылает вопрос мастерам с номером заявки и контактом клиента."""
    if message.from_user is None or message.bot is None:
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(QUESTION_EMPTY, reply_markup=cancel_kb())
        return
    user, _created = await get_or_create_user(session, message.from_user)
    data = await state.get_data()
    ticket_ref = str(data.get("ticket_ref") or "")
    existing = await _local_request(session, user, ticket_ref) if ticket_ref else None
    if existing is not None:
        existing.text = f"{existing.text}\n\nВопрос мастерам:\n{text}"
        existing.admin_reply = None
        existing.status = RequestStatus.NEW
        await session.flush()
        request = existing
        source = request.source.value
    else:
        request = await RequestRepo.create(
            session,
            user_id=user.id,
            request_type=RequestType.QUESTION,
            text=text,
            source=RequestSource.MINIAPP,
            services_text=f"Заявка Mini App №{ticket_ref}" if ticket_ref else None,
        )
        source = RequestSource.QUESTION.value
    await notify_admins(
        message.bot,
        session,
        CONTACT_MASTER_ADMIN.format(
            id=ticket_ref or request.id,
            text=_esc(text),
            **_contact_card(user),
        ),
        reply_markup=admin_request_actions_kb(
            request.id,
            slot=request.desired_slot,
            phone=user.phone,
            source=source,
        ),
    )
    await state.clear()
    await show_screen(message, CONTACT_MASTER_SENT, main_menu_kb())


@router.callback_query(TicketCancelFilter())
async def ticket_cancel(
    callback: CallbackQuery,
    session: AsyncSession,
    ticket_ref: str,
    ticket_action: str,
) -> None:
    """Клиент нажал отмену или перенос на чек-тикете записи."""
    if callback.from_user is None:
        return
    user, _created = await get_or_create_user(session, callback.from_user)
    if user.is_blocked:
        await callback.answer()
        return
    await _revoke(callback, session, user, ticket_ref, ticket_action)


@router.message(Command("cancel_booking"))
async def cmd_cancel_booking(
    message: Message,
    session: AsyncSession,
    command: CommandObject,
) -> None:
    """Команда отмены записи: `/cancel_booking` или `/cancel_booking 12`."""
    if message.from_user is None:
        return
    user, _created = await get_or_create_user(session, message.from_user)
    if user.is_blocked:
        return
    raw = (command.args or "").strip()
    if raw:
        await _revoke(message, session, user, raw, "отмена")
        return
    request = await _latest_active_miniapp(session, user)
    if request is None:
        await show_screen(message, BOOKING_REVOKE_NO_ACTIVE, main_menu_kb())
        return
    await _revoke(message, session, user, str(request.id), "отмена")
