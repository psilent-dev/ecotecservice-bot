"""Админ: новые заявки, открытые диалоги, ответы клиентам."""

from __future__ import annotations

import html
import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import ClientRequest, RequestSource, RequestStatus, User
from database.repo import RequestRepo, UserRepo
from filters.admin import IsAdmin
from handlers.admin_entry import FsmModeFilter
from handlers.start import ack_event, get_or_create_user, show_admin_home, show_screen
from keyboards.inline import (
    MenuCB,
    PageCB,
    RequestCB,
    admin_request_detail_kb,
    cancel_kb,
    client_dialog_kb,
    main_menu_kb,
    requests_list_kb,
)
from services.notify import notify_user
from states.admin import AdminReplyStates
from texts import (
    ADMIN_DIALOGS_EMPTY,
    ADMIN_DIALOGS_HEADER,
    ADMIN_REPLY_EMPTY,
    ADMIN_REPLY_PROMPT,
    ADMIN_REPLY_SENT,
    ADMIN_REQUEST_CLOSED,
    ADMIN_REQUEST_DETAIL,
    ADMIN_REQUEST_LIST_ITEM,
    ADMIN_REQUEST_NO_CAR,
    ADMIN_REQUEST_NOT_FOUND,
    ADMIN_REQUESTS_EMPTY,
    ADMIN_REQUESTS_HEADER,
    BOOKING_CONFIRMED,
    BTN_CANCEL,
    CLIENT_DIALOG_CLOSED,
    FSM_CANCELLED,
    MASTER_TO_CLIENT,
    QUESTION_EMPTY,
    QUESTION_FOLLOWUP_PROMPT,
    QUESTION_PROMPT,
    REQUEST_SOURCE_LABELS,
    REQUEST_STATUS_LABELS,
)
from utils.validators import format_phone_display

PAGE_SIZE = 5
SECTION_NEW = "req_new"
SECTION_DIALOGS = "req_dlg"

router = Router(name="admin_requests")

admin_router = Router(name="admin_requests_staff")
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())

public_router = Router(name="admin_requests_public")


class ClientFollowupStates(StatesGroup):
    """Клиент продолжает переписку по заявке."""

    enter_text = State()


def _esc(value: str) -> str:
    """Экранирует пользовательский текст для HTML."""
    return html.escape(value, quote=False)


def _services_block(request: ClientRequest) -> str:
    """Список услуг из заявки."""
    raw = (request.services_text or "").strip()
    if raw:
        lines = [f"   • {_esc(part.strip(' •-'))}" for part in raw.replace(";", "\n").split("\n") if part.strip()]
        return "\n".join(lines) if lines else "   • не указаны"
    if request.service is not None:
        return f"   • {request.service.label()}"
    return "   • не указаны"


def format_request_detail(request: ClientRequest, user: User) -> str:
    """Детальная карточка заявки."""
    username = f"@{user.username}" if user.username else "—"
    return ADMIN_REQUEST_DETAIL.format(
        id=request.id,
        source=REQUEST_SOURCE_LABELS.get(request.source.value, request.source.value),
        status=REQUEST_STATUS_LABELS.get(request.status.value, request.status.value),
        full_name=_esc(user.full_name),
        username=_esc(username),
        phone=format_phone_display(user.phone) or "не указан",
        car=_esc(request.car_info or ADMIN_REQUEST_NO_CAR),
        services=_services_block(request),
        slot=_esc(request.desired_slot or "не указана"),
        comment=_esc(request.text or "—"),
    )


def list_button_title(request: ClientRequest) -> str:
    """Подпись кнопки в списке заявок."""
    return ADMIN_REQUEST_LIST_ITEM.format(
        id=request.id,
        source=REQUEST_SOURCE_LABELS.get(request.source.value, request.source.value),
        car=(request.car_info or ADMIN_REQUEST_NO_CAR)[:24],
        status=REQUEST_STATUS_LABELS.get(request.status.value, request.status.value),
    )


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


def _page_slice(
    items: list[ClientRequest],
    page: int,
) -> tuple[list[ClientRequest], int, int]:
    """Срез страницы."""
    if not items:
        return [], 1, 1
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    current = min(max(page, 1), total_pages)
    start = (current - 1) * PAGE_SIZE
    return items[start : start + PAGE_SIZE], current, total_pages


async def render_request_list(
    event: Message | CallbackQuery,
    session: AsyncSession,
    *,
    statuses: tuple[RequestStatus, ...],
    section: str,
    page: int,
    empty_text: str,
    header: str,
    oldest_first: bool,
) -> None:
    """Список заявок кнопками + пагинация."""
    items = await RequestRepo.list_by_statuses(session, statuses, oldest_first=oldest_first)
    if not items:
        await show_screen(event, empty_text, await _admin_kb(session))
        return
    chunk, current, total_pages = _page_slice(items, page)
    buttons = [(item.id, list_button_title(item)) for item in chunk]
    await show_screen(
        event,
        header.format(count=len(items)),
        requests_list_kb(buttons, section, current, total_pages),
    )


async def _admin_kb(session: AsyncSession):
    from handlers.start import admin_home_kb

    return await admin_home_kb(session)


@admin_router.callback_query(MenuCB.filter(F.action == "admin_requests"))
async def list_new_requests(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Новые заявки."""
    await callback.answer()
    await state.clear()
    await render_request_list(
        callback,
        session,
        statuses=(RequestStatus.NEW,),
        section=SECTION_NEW,
        page=1,
        empty_text=ADMIN_REQUESTS_EMPTY,
        header=ADMIN_REQUESTS_HEADER,
        oldest_first=True,
    )


@admin_router.callback_query(MenuCB.filter(F.action == "admin_dialogs"))
async def list_open_dialogs(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Открытые диалоги."""
    await callback.answer()
    await state.clear()
    await render_request_list(
        callback,
        session,
        statuses=(RequestStatus.IN_PROGRESS, RequestStatus.ANSWERED),
        section=SECTION_DIALOGS,
        page=1,
        empty_text=ADMIN_DIALOGS_EMPTY,
        header=ADMIN_DIALOGS_HEADER,
        oldest_first=False,
    )


@admin_router.callback_query(PageCB.filter(F.section.in_({SECTION_NEW, SECTION_DIALOGS})))
async def paginate_requests(
    callback: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
) -> None:
    """Страница списка."""
    await callback.answer()
    if callback_data.section == SECTION_NEW:
        await render_request_list(
            callback,
            session,
            statuses=(RequestStatus.NEW,),
            section=SECTION_NEW,
            page=callback_data.page,
            empty_text=ADMIN_REQUESTS_EMPTY,
            header=ADMIN_REQUESTS_HEADER,
            oldest_first=True,
        )
        return
    await render_request_list(
        callback,
        session,
        statuses=(RequestStatus.IN_PROGRESS, RequestStatus.ANSWERED),
        section=SECTION_DIALOGS,
        page=callback_data.page,
        empty_text=ADMIN_DIALOGS_EMPTY,
        header=ADMIN_DIALOGS_HEADER,
        oldest_first=False,
    )


@admin_router.callback_query(RequestCB.filter(F.action == "open"))
async def open_request(
    callback: CallbackQuery,
    callback_data: RequestCB,
    session: AsyncSession,
) -> None:
    """Детальная карточка заявки."""
    await callback.answer()
    request = await get_request_with_user(session, callback_data.request_id)
    if request is None or request.user is None:
        await show_screen(callback, ADMIN_REQUEST_NOT_FOUND.format(id=callback_data.request_id))
        return
    await show_screen(
        callback,
        format_request_detail(request, request.user),
        admin_request_detail_kb(
            request.id,
            slot=request.desired_slot,
            phone=request.user.phone,
        ),
    )


@admin_router.callback_query(RequestCB.filter(F.action == "confirm"))
async def confirm_slot(
    callback: CallbackQuery,
    callback_data: RequestCB,
    session: AsyncSession,
) -> None:
    """Подтверждает время записи клиенту."""
    await callback.answer()
    request = await get_request_with_user(session, callback_data.request_id)
    if request is None or request.user is None:
        await show_screen(callback, ADMIN_REQUEST_NOT_FOUND.format(id=callback_data.request_id))
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.IN_PROGRESS)
    slot = request.desired_slot or "согласованное время"
    if callback.message and callback.message.bot:
        await notify_user(
            callback.message.bot,
            request.user.tg_id,
            BOOKING_CONFIRMED.format(id=request.id, slot=slot),
            session=session,
        )
    await show_screen(
        callback,
        format_request_detail(request, request.user) + f"\n\n✅ Время подтверждено: {slot}",
        admin_request_detail_kb(request.id, slot=request.desired_slot, phone=request.user.phone),
    )


@admin_router.callback_query(RequestCB.filter(F.action == "reply"))
async def admin_start_reply(
    callback: CallbackQuery,
    callback_data: RequestCB,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Запрашивает текст ответа."""
    await callback.answer()
    request = await get_request_with_user(session, callback_data.request_id)
    if request is None:
        await show_screen(callback, ADMIN_REQUEST_NOT_FOUND.format(id=callback_data.request_id))
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.IN_PROGRESS)
    await state.set_state(AdminReplyStates.enter_reply)
    await state.update_data(mode="request", request_id=request.id)
    await show_screen(callback, ADMIN_REPLY_PROMPT.format(id=request.id), cancel_kb())


@admin_router.callback_query(
    AdminReplyStates.enter_reply,
    FsmModeFilter("request"),
    MenuCB.filter(F.action == "cancel"),
)
@admin_router.message(AdminReplyStates.enter_reply, FsmModeFilter("request"), F.text == BTN_CANCEL)
async def admin_reply_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена ответа."""
    await ack_event(event)
    await state.clear()
    await show_admin_home(event, session)


@admin_router.message(AdminReplyStates.enter_reply, FsmModeFilter("request"), F.text)
async def admin_send_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Пишет клиенту и помечает заявку отвеченной."""
    if message.from_user is None or message.bot is None:
        return
    reply = (message.text or "").strip()
    if not reply:
        await message.answer(ADMIN_REPLY_EMPTY, reply_markup=cancel_kb())
        return
    data = await state.get_data()
    request_id = int(data["request_id"])
    admin, _created = await get_or_create_user(session, message.from_user)
    if not admin.is_admin:
        await state.clear()
        return
    request = await RequestRepo.set_reply(session, request_id, reply, admin.id)
    request = await get_request_with_user(session, request_id) if request is not None else None
    if request is None or request.user is None:
        await state.clear()
        await show_admin_home(message, session)
        return
    await notify_user(
        message.bot,
        request.user.tg_id,
        MASTER_TO_CLIENT.format(id=request.id, reply=_esc(reply)),
        reply_markup=client_dialog_kb(request.id),
        session=session,
    )
    await state.clear()
    await message.answer(ADMIN_REPLY_SENT)
    await show_admin_home(message, session)


@admin_router.callback_query(RequestCB.filter(F.action == "close"))
async def admin_close_request(
    callback: CallbackQuery,
    callback_data: RequestCB,
    session: AsyncSession,
) -> None:
    """Закрывает заявку."""
    await callback.answer()
    request = await get_request_with_user(session, callback_data.request_id)
    if request is None:
        await show_screen(callback, ADMIN_REQUEST_NOT_FOUND.format(id=callback_data.request_id))
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.CLOSED)
    if request.user is not None and callback.message and callback.message.bot:
        await notify_user(
            callback.message.bot,
            request.user.tg_id,
            CLIENT_DIALOG_CLOSED.format(request_id=request.id),
            session=session,
        )
    await show_screen(callback, ADMIN_REQUEST_CLOSED.format(request_id=request.id), await _admin_kb(session))


@public_router.callback_query(RequestCB.filter(F.action == "reply"))
async def client_followup_start(
    callback: CallbackQuery,
    callback_data: RequestCB,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Клиент отвечает мастеру."""
    await callback.answer()
    if callback.from_user is None:
        return
    request = await get_request_with_user(session, callback_data.request_id)
    if request is None or request.user is None or request.user.tg_id != callback.from_user.id:
        return
    await state.set_state(ClientFollowupStates.enter_text)
    await state.update_data(followup_request_id=request.id)
    await show_screen(callback, QUESTION_FOLLOWUP_PROMPT.format(id=request.id), cancel_kb())


@public_router.callback_query(ClientFollowupStates.enter_text, MenuCB.filter(F.action == "cancel"))
@public_router.message(ClientFollowupStates.enter_text, F.text == BTN_CANCEL)
async def client_followup_cancel(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Клиент отменяет продолжение переписки."""
    await ack_event(event)
    await state.clear()
    await show_screen(event, FSM_CANCELLED, main_menu_kb())


@public_router.message(ClientFollowupStates.enter_text, F.text)
async def client_followup_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Добавляет сообщение клиента и возвращает заявку админам."""
    if message.from_user is None or message.bot is None:
        return
    extra = (message.text or "").strip()
    if not extra:
        await message.answer(QUESTION_EMPTY, reply_markup=cancel_kb())
        return
    data = await state.get_data()
    request = await get_request_with_user(session, int(data["followup_request_id"]))
    if request is None or request.user is None or request.user.tg_id != message.from_user.id:
        await state.clear()
        return
    request.text = f"{request.text}\n\n{extra}"
    request.admin_reply = None
    request.status = RequestStatus.NEW
    await session.flush()
    from handlers.booking import format_quick_card, format_miniapp_card
    from keyboards.inline import admin_request_actions_kb
    from services.notify import notify_admins

    if request.source is RequestSource.MINIAPP:
        card = format_miniapp_card(
            request.id,
            request.user,
            car=request.car_info or "",
            services=request.services_text or "",
            slot=request.desired_slot or "",
            comment=request.text,
        )
    else:
        card = format_quick_card(request.id, request.user, extra)
    await notify_admins(
        message.bot,
        session,
        card,
        reply_markup=admin_request_actions_kb(
            request.id,
            slot=request.desired_slot,
            phone=request.user.phone,
            source=request.source.value,
        ),
    )
    await state.clear()
    await show_screen(message, "Сообщение передано мастеру.", main_menu_kb())


@public_router.callback_query(RequestCB.filter(F.action == "close"))
async def client_close_request(
    callback: CallbackQuery,
    callback_data: RequestCB,
    session: AsyncSession,
) -> None:
    """Клиент закрывает диалог."""
    await callback.answer()
    if callback.from_user is None:
        return
    request = await get_request_with_user(session, callback_data.request_id)
    if request is None or request.user is None or request.user.tg_id != callback.from_user.id:
        return
    await RequestRepo.update_status(session, request.id, RequestStatus.CLOSED)
    await show_screen(
        callback,
        CLIENT_DIALOG_CLOSED.format(request_id=request.id),
        main_menu_kb(),
    )


router.include_router(admin_router)
router.include_router(public_router)
