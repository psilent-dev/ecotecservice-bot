"""Админ: новые и отвеченные заявки, ответы клиентам."""

from __future__ import annotations

import html
import math
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database.models import ClientRequest, RequestStatus, User
from database.repo import RequestRepo, UserRepo
from filters.admin import IsAdmin
from handlers.admin_entry import FsmModeFilter
from handlers.start import menu_kb
from keyboards.reply import (
    ADMIN_BTN_ANSWERED,
    admin_menu_kb,
    cancel_kb,
    client_dialog_kb,
    list_kb,
    main_menu_kb,
    numbered_label,
    parse_numbered,
    parse_trailing_num,
    request_actions_kb,
)
from services.notify import notify_admins, notify_user
from states.admin import AdminPickStates, AdminReplyStates
from texts import (
    ADMIN_MENU_BUTTONS,
    ADMIN_REPLY_EMPTY,
    ADMIN_REPLY_PROMPT,
    ADMIN_REPLY_SENT,
    ADMIN_REPLY_TO_CLIENT,
    ADMIN_REQUEST_CARD,
    ADMIN_REQUEST_CLOSED,
    ADMIN_REQUEST_NO_CAR,
    ADMIN_REQUEST_NO_SERVICE,
    ADMIN_REQUEST_NOT_FOUND,
    ADMIN_REQUESTS_EMPTY,
    ADMIN_REQUESTS_HEADER,
    ADMIN_TAKE_IN_PROGRESS,
    BTN_BACK,
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_MAIN_MENU,
    BTN_PAGE_NEXT,
    BTN_PAGE_PREV,
    BTN_REOPEN,
    BTN_REPLY,
    BTN_REPLY_AGAIN,
    FSM_CANCELLED,
    PROFILE_NO_PHONE,
    QUESTION_CREATED,
    QUESTION_EMPTY,
    QUESTION_PROMPT,
    REQUEST_STATUS_LABELS,
    REQUEST_TYPE_LABELS,
)

PAGE_SIZE = 5
_CLIENT_REPLY_RE = re.compile(rf"^{re.escape(BTN_REPLY_AGAIN)} №\d+")
_CLIENT_CLOSE_RE = re.compile(rf"^{re.escape(BTN_CLOSE)} №\d+")

router = Router(name="admin_requests")

admin_router = Router(name="admin_requests_staff")
admin_router.message.filter(IsAdmin())

public_router = Router(name="admin_requests_public")


class ClientFollowupStates(StatesGroup):
    """Клиент продолжает переписку по существующей заявке."""

    enter_text = State()


def _esc(value: str) -> str:
    """Экранирует пользовательский текст для HTML parse_mode."""
    return html.escape(value, quote=False)


def _when(value: datetime | None) -> str:
    """Дата-время в часовом поясе сервиса."""
    if value is None:
        return ADMIN_REQUEST_NO_CAR
    moment = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(settings.tz)).strftime("%d.%m.%Y %H:%M")


def format_request_card(request: ClientRequest, user: User) -> str:
    """Карточка заявки из констант texts.py."""
    service = (
        request.service.label()
        if request.service is not None
        else ADMIN_REQUEST_NO_SERVICE
    )
    body = request.text
    if request.admin_reply:
        body = (
            f"{body}\n\n{_when(request.answered_at)}\n"
            f"{ADMIN_REPLY_TO_CLIENT.format(id=request.id, reply=request.admin_reply)}"
        )
    username = f"@{user.username}" if user.username else ADMIN_REQUEST_NO_CAR
    header = (
        f"Заявка №{request.id} | "
        f"{REQUEST_TYPE_LABELS.get(request.type.value, request.type.value)} | "
        f"{_when(request.created_at)}\n"
        f"От: {_esc(user.full_name)} ({_esc(username)})"
    )
    card = ADMIN_REQUEST_CARD.format(
        id=request.id,
        type=REQUEST_TYPE_LABELS.get(request.type.value, request.type.value),
        status=REQUEST_STATUS_LABELS.get(request.status.value, request.status.value),
        full_name=_esc(user.full_name),
        tg_id=user.tg_id,
        phone=_esc(user.phone or PROFILE_NO_PHONE),
        service=_esc(service),
        car_info=_esc(request.car_info or ADMIN_REQUEST_NO_CAR),
        text=_esc(body),
    )
    return f"{header}\n\n{card}"


async def get_request_with_user(
    session: AsyncSession,
    request_id: int,
) -> ClientRequest | None:
    """Заявка вместе с клиентом."""
    result = await session.execute(
        select(ClientRequest)
        .options(selectinload(ClientRequest.user))
        .where(ClientRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def load_requests(
    session: AsyncSession,
    statuses: tuple[RequestStatus, ...],
) -> list[ClientRequest]:
    """Заявки указанных статусов: NEW — старые первыми, остальные — новые сверху."""
    stmt = (
        select(ClientRequest)
        .options(selectinload(ClientRequest.user))
        .where(ClientRequest.status.in_(statuses))
    )
    if statuses == (RequestStatus.NEW,):
        stmt = stmt.order_by(ClientRequest.created_at.asc())
    else:
        stmt = stmt.order_by(ClientRequest.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _page_slice(
    items: list[ClientRequest],
    page: int,
) -> tuple[list[ClientRequest], int, int]:
    """Возвращает срез страницы, текущий номер и общее число страниц."""
    if not items:
        return [], 1, 1
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    current = min(max(page, 1), total_pages)
    start = (current - 1) * PAGE_SIZE
    return items[start : start + PAGE_SIZE], current, total_pages


async def render_request_page(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    statuses: tuple[RequestStatus, ...],
    pick_state: State,
    page: int,
    empty_text: str,
) -> None:
    """Печатает страницу заявок reply-кнопками."""
    items = await load_requests(session, statuses)
    if not items:
        await state.clear()
        await message.answer(empty_text, reply_markup=admin_menu_kb())
        return
    chunk, current, total_pages = _page_slice(items, page)
    await state.set_state(pick_state)
    await state.update_data(req_page=current, req_total=total_pages)
    labels = [
        numbered_label(
            item.id,
            REQUEST_TYPE_LABELS.get(item.type.value, item.type.value),
        )
        for item in chunk
    ]
    await message.answer(ADMIN_REQUESTS_HEADER.format(count=len(items)))
    for request in chunk:
        await message.answer(format_request_card(request, request.user))
    await message.answer(
        ADMIN_REQUESTS_HEADER.format(count=len(items)),
        reply_markup=list_kb(labels, page=current, total_pages=total_pages),
    )


async def _show_new(message: Message, state: FSMContext, session: AsyncSession, page: int) -> None:
    """Страница новых заявок."""
    await render_request_page(
        message,
        state,
        session,
        statuses=(RequestStatus.NEW,),
        pick_state=AdminPickStates.requests_new,
        page=page,
        empty_text=ADMIN_REQUESTS_EMPTY,
    )


async def _show_done(message: Message, state: FSMContext, session: AsyncSession, page: int) -> None:
    """Страница отвеченных и закрытых."""
    await render_request_page(
        message,
        state,
        session,
        statuses=(RequestStatus.ANSWERED, RequestStatus.CLOSED),
        pick_state=AdminPickStates.requests_done,
        page=page,
        empty_text=ADMIN_REQUESTS_HEADER.format(count=0),
    )


@admin_router.message(F.text == ADMIN_MENU_BUTTONS["requests"])
async def list_new_requests(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Новые заявки."""
    await _show_new(message, state, session, 1)


@admin_router.message(F.text == ADMIN_BTN_ANSWERED)
async def list_done_requests(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Отвеченные и закрытые заявки."""
    await _show_done(message, state, session, 1)


@admin_router.message(AdminPickStates.requests_new, F.text == BTN_BACK)
@admin_router.message(AdminPickStates.requests_done, F.text == BTN_BACK)
@admin_router.message(AdminPickStates.request_actions, F.text == BTN_BACK)
async def requests_back(message: Message, state: FSMContext) -> None:
    """Назад в админ-меню."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@admin_router.message(AdminPickStates.requests_new, F.text == BTN_PAGE_NEXT)
async def new_next(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Следующая страница новых."""
    data = await state.get_data()
    await _show_new(message, state, session, int(data.get("req_page", 1)) + 1)


@admin_router.message(AdminPickStates.requests_new, F.text == BTN_PAGE_PREV)
async def new_prev(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Предыдущая страница новых."""
    data = await state.get_data()
    await _show_new(message, state, session, int(data.get("req_page", 1)) - 1)


@admin_router.message(AdminPickStates.requests_done, F.text == BTN_PAGE_NEXT)
async def done_next(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Следующая страница отвеченных."""
    data = await state.get_data()
    await _show_done(message, state, session, int(data.get("req_page", 1)) + 1)


@admin_router.message(AdminPickStates.requests_done, F.text == BTN_PAGE_PREV)
async def done_prev(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Предыдущая страница отвеченных."""
    data = await state.get_data()
    await _show_done(message, state, session, int(data.get("req_page", 1)) - 1)


@admin_router.message(AdminPickStates.requests_new, F.text.regexp(r"^№\d+"))
@admin_router.message(AdminPickStates.requests_done, F.text.regexp(r"^№\d+"))
async def pick_request(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Выбор заявки по кнопке №id."""
    request_id = parse_numbered(message.text or "")
    if request_id is None:
        return
    request = await get_request_with_user(session, request_id)
    if request is None:
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id), reply_markup=admin_menu_kb())
        await state.clear()
        return
    await state.set_state(AdminPickStates.request_actions)
    await state.update_data(request_id=request.id)
    await message.answer(format_request_card(request, request.user), reply_markup=request_actions_kb())


@admin_router.message(AdminPickStates.request_actions, F.text == BTN_REPLY)
async def admin_start_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Запрашивает текст ответа администратора."""
    data = await state.get_data()
    request_id = int(data["request_id"])
    request = await get_request_with_user(session, request_id)
    if request is None:
        await state.clear()
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id), reply_markup=admin_menu_kb())
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.IN_PROGRESS)
    await state.set_state(AdminReplyStates.enter_reply)
    await state.update_data(mode="request", request_id=request.id)
    await message.answer(ADMIN_REPLY_PROMPT.format(id=request.id), reply_markup=cancel_kb())


@admin_router.message(AdminReplyStates.enter_reply, FsmModeFilter("request"), F.text == BTN_CANCEL)
async def admin_reply_cancel(message: Message, state: FSMContext) -> None:
    """Отмена ответа."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@admin_router.message(AdminReplyStates.enter_reply, FsmModeFilter("request"), F.text)
async def admin_send_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сохраняет ответ, пишет клиенту и помечает заявку отвеченной."""
    if message.from_user is None or message.bot is None:
        return
    reply = (message.text or "").strip()
    if not reply:
        await message.answer(ADMIN_REPLY_EMPTY, reply_markup=cancel_kb())
        return
    data = await state.get_data()
    request_id = int(data["request_id"])
    admin = await UserRepo.get_by_tg_id(session, message.from_user.id)
    if admin is None:
        await state.clear()
        return
    request = await RequestRepo.set_reply(session, request_id, reply, admin.id)
    if request is None:
        await state.clear()
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id), reply_markup=admin_menu_kb())
        return
    request = await get_request_with_user(session, request_id)
    if request is None or request.user is None:
        await state.clear()
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id), reply_markup=admin_menu_kb())
        return
    await notify_user(
        message.bot,
        request.user.tg_id,
        ADMIN_REPLY_TO_CLIENT.format(id=request.id, reply=_esc(reply)),
        reply_markup=client_dialog_kb(request.id),
        session=session,
    )
    await state.clear()
    await message.answer(ADMIN_REPLY_SENT, reply_markup=admin_menu_kb())


@admin_router.message(AdminPickStates.request_actions, F.text == BTN_CLOSE)
async def admin_close_request(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Закрывает заявку и уведомляет клиента."""
    if message.bot is None:
        return
    data = await state.get_data()
    request_id = int(data["request_id"])
    request = await get_request_with_user(session, request_id)
    await state.clear()
    if request is None:
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id), reply_markup=admin_menu_kb())
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.CLOSED)
    if request.user is not None:
        await notify_user(
            message.bot,
            request.user.tg_id,
            ADMIN_REQUEST_CLOSED.format(request_id=request.id),
            session=session,
        )
    await message.answer(
        ADMIN_REQUEST_CLOSED.format(request_id=request.id),
        reply_markup=admin_menu_kb(),
    )


@admin_router.message(AdminPickStates.request_actions, F.text == BTN_REOPEN)
async def admin_reopen_request(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Возвращает заявку в работу."""
    data = await state.get_data()
    request_id = int(data["request_id"])
    request = await RequestRepo.update_status(session, request_id, RequestStatus.IN_PROGRESS)
    await state.clear()
    if request is None:
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id), reply_markup=admin_menu_kb())
        return
    await message.answer(
        ADMIN_TAKE_IN_PROGRESS.format(id=request.id),
        reply_markup=admin_menu_kb(),
    )


@public_router.message(F.text.regexp(_CLIENT_REPLY_RE))
async def client_followup_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Клиент продолжает диалог по заявке."""
    if message.from_user is None:
        return
    request_id = parse_trailing_num(message.text or "")
    if request_id is None:
        return
    request = await get_request_with_user(session, request_id)
    if request is None or request.user is None or request.user.tg_id != message.from_user.id:
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id or 0))
        return
    await state.set_state(ClientFollowupStates.enter_text)
    await state.update_data(followup_request_id=request.id)
    await message.answer(QUESTION_PROMPT, reply_markup=cancel_kb())


@public_router.message(ClientFollowupStates.enter_text, F.text == BTN_CANCEL)
async def client_followup_cancel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Клиент отменяет продолжение переписки."""
    await state.clear()
    if message.from_user is None:
        await message.answer(FSM_CANCELLED, reply_markup=main_menu_kb())
        return
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    await message.answer(FSM_CANCELLED, reply_markup=menu_kb(user) if user else main_menu_kb())


@public_router.message(ClientFollowupStates.enter_text, F.text)
async def client_followup_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Добавляет сообщение клиента в заявку и возвращает её админам."""
    if message.from_user is None or message.bot is None:
        return
    extra = (message.text or "").strip()
    if not extra:
        await message.answer(QUESTION_EMPTY, reply_markup=cancel_kb())
        return
    data = await state.get_data()
    request_id = int(data["followup_request_id"])
    request = await get_request_with_user(session, request_id)
    if request is None or request.user is None or request.user.tg_id != message.from_user.id:
        await state.clear()
        await message.answer(ADMIN_REQUEST_NOT_FOUND.format(id=request_id))
        return
    history = request.text
    if request.admin_reply:
        history = f"{history}\n\n{request.admin_reply}"
    request.text = f"{history}\n\n{extra}"
    request.admin_reply = None
    request.status = RequestStatus.NEW
    await session.flush()
    await notify_admins(
        message.bot,
        session,
        format_request_card(request, request.user),
        reply_markup=admin_menu_kb(),
    )
    await state.clear()
    await message.answer(
        QUESTION_CREATED.format(request_id=request.id),
        reply_markup=main_menu_kb(),
    )


@public_router.message(F.text.regexp(_CLIENT_CLOSE_RE))
async def client_close_request(message: Message, session: AsyncSession) -> None:
    """Клиент закрывает свою заявку."""
    if message.from_user is None:
        return
    request_id = parse_trailing_num(message.text or "")
    if request_id is None:
        return
    request = await get_request_with_user(session, request_id)
    if request is None or request.user is None or request.user.tg_id != message.from_user.id:
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.CLOSED)
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    await message.answer(
        ADMIN_REQUEST_CLOSED.format(request_id=request.id),
        reply_markup=menu_kb(user) if user else main_menu_kb(),
    )


@public_router.message(F.text == BTN_MAIN_MENU)
async def client_dialog_menu(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """С диалога заявки — в главное меню."""
    await state.clear()
    if message.from_user is None:
        await message.answer(FSM_CANCELLED, reply_markup=main_menu_kb())
        return
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    await message.answer(FSM_CANCELLED, reply_markup=menu_kb(user) if user else main_menu_kb())


router.include_router(admin_router)
router.include_router(public_router)
