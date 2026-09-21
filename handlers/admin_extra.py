"""Клиенты, статистика, бонусы и выход в клиентское меню."""

from __future__ import annotations

import html
from collections.abc import Awaitable, Callable
from math import ceil
from typing import Any

from aiogram import BaseMiddleware, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from database.repo import RequestRepo, UserRepo
from filters.admin import IsAdmin
from handlers.admin_entry import FsmModeFilter
from handlers.start import ack_event, menu_kb, show_admin_home, show_screen, start_text
from keyboards.inline import (
    NEW_ITEM_ID,
    ClientCB,
    MenuCB,
    PageCB,
    cancel_kb,
    client_card_kb,
    pagination_kb,
)
from services.notify import notify_user
from states.admin import AdminBonusStates, AdminReplyStates, AdminSearchStates
from texts import (
    ADMIN_ADMIN_NO_USERNAME,
    ADMIN_BONUS_ADDED,
    ADMIN_BONUS_INVALID,
    ADMIN_BONUS_PROMPT,
    ADMIN_CLIENT_CARD,
    ADMIN_CLIENT_ITEM,
    ADMIN_CLIENT_NOT_FOUND,
    ADMIN_CLIENT_SEARCH_PROMPT,
    ADMIN_CLIENTS_EMPTY,
    ADMIN_CLIENTS_HEADER,
    ADMIN_GIFT_TO_CLIENT,
    ADMIN_REPLY_EMPTY,
    ADMIN_REPLY_PROMPT,
    ADMIN_REPLY_SENT,
    ADMIN_STATS,
    BTN_CANCEL,
    FSM_CANCELLED,
    PHONE_NOT_BOUND,
    USER_BLOCKED,
)
from utils.validators import format_phone_display

PAGE_SIZE = 10
SECTION_CLIENTS = "clients"

accepting_requests: bool = True

router = Router(name="admin_extra")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AcceptingRequestsMiddleware(BaseMiddleware):
    """Резерв: приём заявок всегда включён (переключатель убран из UI)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        return await handler(event, data)


class BlockedUserMiddleware(BaseMiddleware):
    """Заблокированный клиент не проходит дальше; администраторы не затрагиваются."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")
        from_user = data.get("event_from_user")
        if session is None or from_user is None:
            return await handler(event, data)
        db_user = await UserRepo.get_by_tg_id(session, from_user.id)
        if db_user is None or not db_user.is_blocked or db_user.is_admin:
            return await handler(event, data)
        text = USER_BLOCKED.format(phone=settings.service_phone)
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        return None


def format_client_card(user: User) -> str:
    """Карточка клиента."""
    username = user.username or ADMIN_ADMIN_NO_USERNAME
    return ADMIN_CLIENT_CARD.format(
        full_name=html.escape(user.full_name, quote=False),
        tg_id=user.tg_id,
        username=html.escape(username, quote=False),
        phone=format_phone_display(user.phone) or PHONE_NOT_BOUND,
        balance=user.bonus_balance,
        visits_count=user.visits_count,
    )


def clients_page_kb(users: list[User], page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Список клиентов страницы."""
    builder = InlineKeyboardBuilder()
    for user in users:
        builder.row(
            InlineKeyboardButton(
                text=ADMIN_CLIENT_ITEM.format(
                    full_name=user.full_name[:24],
                    phone=format_phone_display(user.phone) or PHONE_NOT_BOUND,
                    visits_count=user.visits_count,
                )[:64],
                callback_data=ClientCB(action="open", user_id=user.id).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔎 Поиск",
            callback_data=ClientCB(action="search", user_id=NEW_ITEM_ID).pack(),
        )
    )
    if total_pages > 1:
        builder.attach(
            InlineKeyboardBuilder.from_markup(pagination_kb(SECTION_CLIENTS, page, total_pages))
        )
    return builder.as_markup()


async def render_clients_page(
    event: Message | CallbackQuery,
    session: AsyncSession,
    page: int,
) -> None:
    """Страница базы клиентов."""
    total = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    if total == 0:
        await show_screen(event, ADMIN_CLIENTS_EMPTY, await _home(session))
        return
    total_pages = max(1, ceil(total / PAGE_SIZE))
    current = min(max(page, 1), total_pages)
    users = await UserRepo.list_clients(session, (current - 1) * PAGE_SIZE, PAGE_SIZE)
    await show_screen(
        event,
        ADMIN_CLIENTS_HEADER.format(page=current),
        clients_page_kb(users, current, total_pages),
    )


async def _home(session: AsyncSession) -> InlineKeyboardMarkup:
    from handlers.start import admin_home_kb

    return await admin_home_kb(session)


@router.callback_query(MenuCB.filter(F.action == "admin_clients"))
async def clients_root(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """База клиентов."""
    await callback.answer()
    await state.clear()
    await render_clients_page(callback, session, 1)


@router.callback_query(PageCB.filter(F.section == SECTION_CLIENTS))
async def clients_page(
    callback: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
) -> None:
    """Страница клиентов."""
    await callback.answer()
    await render_clients_page(callback, session, callback_data.page)


@router.callback_query(ClientCB.filter(F.action == "search"))
async def clients_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос строки поиска."""
    await callback.answer()
    await state.set_state(AdminSearchStates.enter_query)
    await show_screen(callback, ADMIN_CLIENT_SEARCH_PROMPT, cancel_kb())


@router.callback_query(AdminSearchStates.enter_query, MenuCB.filter(F.action == "cancel"))
@router.message(AdminSearchStates.enter_query, F.text == BTN_CANCEL)
async def clients_search_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена поиска."""
    await ack_event(event)
    await state.clear()
    await show_admin_home(event, session)


@router.message(AdminSearchStates.enter_query, F.text)
async def clients_search_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Поиск по имени, телефону или госномеру."""
    query = (message.text or "").strip()
    await state.clear()
    users = await UserRepo.search_clients(session, query)
    if not users:
        await message.answer(
            ADMIN_CLIENT_NOT_FOUND.format(query=html.escape(query, quote=False)),
        )
        await show_admin_home(message, session)
        return
    builder = InlineKeyboardBuilder()
    for user in users[:20]:
        builder.row(
            InlineKeyboardButton(
                text=ADMIN_CLIENT_ITEM.format(
                    full_name=user.full_name[:24],
                    phone=format_phone_display(user.phone) or PHONE_NOT_BOUND,
                    visits_count=user.visits_count,
                )[:64],
                callback_data=ClientCB(action="open", user_id=user.id).pack(),
            )
        )
    await message.answer(ADMIN_CLIENTS_HEADER.format(page=1), reply_markup=builder.as_markup())


@router.callback_query(ClientCB.filter(F.action == "open"))
async def client_open(
    callback: CallbackQuery,
    callback_data: ClientCB,
    session: AsyncSession,
) -> None:
    """Карточка клиента."""
    await callback.answer()
    user = await session.get(User, callback_data.user_id)
    if user is None:
        await show_screen(callback, ADMIN_CLIENT_NOT_FOUND.format(query=str(callback_data.user_id)))
        return
    await show_screen(
        callback,
        format_client_card(user),
        client_card_kb(user.id, is_blocked=user.is_blocked),
    )


@router.callback_query(ClientCB.filter(F.action == "write"))
async def client_write_start(
    callback: CallbackQuery,
    callback_data: ClientCB,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Личное сообщение клиенту."""
    await callback.answer()
    user = await session.get(User, callback_data.user_id)
    if user is None:
        await show_screen(callback, ADMIN_CLIENT_NOT_FOUND.format(query=str(callback_data.user_id)))
        return
    await state.set_state(AdminReplyStates.enter_reply)
    await state.update_data(mode="direct", target_user_id=user.id)
    await show_screen(callback, ADMIN_REPLY_PROMPT.format(id=user.tg_id), cancel_kb())


@router.callback_query(
    AdminReplyStates.enter_reply,
    FsmModeFilter("direct"),
    MenuCB.filter(F.action == "cancel"),
)
@router.message(AdminReplyStates.enter_reply, FsmModeFilter("direct"), F.text == BTN_CANCEL)
async def client_write_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена личного сообщения."""
    await ack_event(event)
    await state.clear()
    await show_admin_home(event, session)


@router.message(AdminReplyStates.enter_reply, FsmModeFilter("direct"), F.text)
async def client_write_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отправляет произвольное сообщение."""
    if message.bot is None:
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(ADMIN_REPLY_EMPTY, reply_markup=cancel_kb())
        return
    data = await state.get_data()
    user = await session.get(User, int(data["target_user_id"]))
    await state.clear()
    if user is None:
        await show_admin_home(message, session)
        return
    await notify_user(message.bot, user.tg_id, text, session=session)
    await message.answer(ADMIN_REPLY_SENT)
    await show_admin_home(message, session)


@router.callback_query(ClientCB.filter(F.action == "bonus"))
async def client_bonus_start(
    callback: CallbackQuery,
    callback_data: ClientCB,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Запрашивает сумму бонусов."""
    await callback.answer()
    user = await session.get(User, callback_data.user_id)
    if user is None:
        await show_screen(callback, ADMIN_CLIENT_NOT_FOUND.format(query=str(callback_data.user_id)))
        return
    await state.set_state(AdminBonusStates.enter_amount)
    await state.update_data(target_user_id=user.id)
    await show_screen(callback, ADMIN_BONUS_PROMPT, cancel_kb())


@router.callback_query(AdminBonusStates.enter_amount, MenuCB.filter(F.action == "cancel"))
@router.message(AdminBonusStates.enter_amount, F.text == BTN_CANCEL)
async def client_bonus_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена начисления."""
    await ack_event(event)
    await state.clear()
    await show_admin_home(event, session)


@router.message(AdminBonusStates.enter_amount, F.text)
async def client_bonus_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Начисляет бонусы и пишет клиенту."""
    if message.bot is None:
        return
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(ADMIN_BONUS_INVALID, reply_markup=cancel_kb())
        return
    amount = int(raw)
    data = await state.get_data()
    user = await UserRepo.add_bonus(session, int(data["target_user_id"]), amount)
    await state.clear()
    if user is None:
        await show_admin_home(message, session)
        return
    await notify_user(
        message.bot,
        user.tg_id,
        ADMIN_GIFT_TO_CLIENT.format(
            service_name=settings.service_name,
            text=f"На ваш баланс начислено {amount} ₽ бонусов.",
        ),
        session=session,
    )
    await message.answer(ADMIN_BONUS_ADDED.format(amount=amount, balance=user.bonus_balance))
    await show_admin_home(message, session)


@router.callback_query(ClientCB.filter(F.action.in_({"block", "unblock"})))
async def client_toggle_block(
    callback: CallbackQuery,
    callback_data: ClientCB,
    session: AsyncSession,
) -> None:
    """Блокирует или разблокирует клиента."""
    await callback.answer()
    user = await session.get(User, callback_data.user_id)
    if user is None:
        await show_screen(callback, ADMIN_CLIENT_NOT_FOUND.format(query=str(callback_data.user_id)))
        return
    user.is_blocked = callback_data.action == "block"
    await session.flush()
    await show_screen(
        callback,
        format_client_card(user),
        client_card_kb(user.id, is_blocked=user.is_blocked),
    )


@router.callback_query(MenuCB.filter(F.action == "admin_stats"))
async def show_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """Заявки за день / неделю / месяц."""
    await callback.answer()
    stats = await RequestRepo.stats(session)
    await show_screen(callback, ADMIN_STATS.format(**stats), await _home(session))


@router.callback_query(MenuCB.filter(F.action == "admin_exit"))
async def back_to_client_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Возврат администратора в клиентское меню."""
    await callback.answer()
    await state.clear()
    if callback.from_user is None:
        return
    user = await UserRepo.get_by_tg_id(session, callback.from_user.id)
    if user is None:
        return
    await show_screen(callback, start_text(), menu_kb(user))
