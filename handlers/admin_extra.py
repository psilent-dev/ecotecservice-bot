"""Клиенты, настройки, пауза приёма заявок и выход в клиентское меню."""

from __future__ import annotations

import html
from collections.abc import Awaitable, Callable
from math import ceil
from typing import Any

from aiogram import BaseMiddleware, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from database.repo import UserRepo
from filters.admin import IsAdmin
from handlers.admin_entry import FsmModeFilter
from keyboards.reply import (
    ADMIN_BTN_TO_CLIENT,
    admin_menu_kb,
    cancel_kb,
    client_card_kb,
    list_kb,
    main_menu_kb,
    numbered_label,
    parse_numbered,
    settings_kb,
)
from services.loyalty import get_active_bonuses
from services.notify import notify_user
from states.admin import (
    AdminBonusStates,
    AdminPickStates,
    AdminReplyStates,
    AdminSearchStates,
)
from states.client import BookingStates, PriceStates, QuestionStates
from texts import (
    ADMIN_ACCESS_DENIED,
    ADMIN_ADMIN_NO_USERNAME,
    ADMIN_CLIENT_CARD,
    ADMIN_CLIENT_NOT_FOUND,
    ADMIN_CLIENT_SEARCH_PROMPT,
    ADMIN_CLIENTS_EMPTY,
    ADMIN_CLIENTS_HEADER,
    ADMIN_FLAG_NO,
    ADMIN_FLAG_YES,
    ADMIN_GIFT_TO_CLIENT,
    ADMIN_MENU_BUTTONS,
    ADMIN_REPLY_EMPTY,
    ADMIN_REPLY_PROMPT,
    ADMIN_REPLY_SENT,
    ADMIN_SETTINGS_TEXT,
    BTN_ACCEPT_OFF,
    BTN_ACCEPT_ON,
    BTN_BACK,
    BTN_BLOCK,
    BTN_CANCEL,
    BTN_GIFT,
    BTN_PAGE_NEXT,
    BTN_PAGE_PREV,
    BTN_SEARCH,
    BTN_UNBLOCK,
    BTN_WRITE,
    ERROR_GLOBAL,
    FSM_CANCELLED,
    MENU_BUTTONS,
    MENU_MAIN,
    PROFILE_NO_PHONE,
    USER_BLOCKED,
)

PAGE_SIZE = 10

accepting_requests: bool = True

router = Router(name="admin_extra")
router.message.filter(IsAdmin())

_NEW_REQUEST_TEXTS = {
    MENU_BUTTONS["booking"],
    MENU_BUTTONS["price"],
    MENU_BUTTONS["question"],
}
_BLOCKED_STATE_PREFIXES = (
    BookingStates.__name__,
    PriceStates.__name__,
    QuestionStates.__name__,
)


class AcceptingRequestsMiddleware(BaseMiddleware):
    """Если приём заявок выключен — не даёт создавать новые записи, цены и вопросы."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Пропускает апдейт либо отвечает ERROR_GLOBAL."""
        if accepting_requests:
            return await handler(event, data)

        blocked = False
        if isinstance(event, Message) and event.text in _NEW_REQUEST_TEXTS:
            blocked = True

        state: FSMContext | None = data.get("state")
        if state is not None:
            current = await state.get_state()
            if current is not None and current.split(":")[0] in _BLOCKED_STATE_PREFIXES:
                blocked = True

        if not blocked:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(ERROR_GLOBAL)
        elif isinstance(event, CallbackQuery):
            await event.answer(ERROR_GLOBAL, show_alert=True)
        return None


class BlockedUserMiddleware(BaseMiddleware):
    """Заблокированный клиент не проходит дальше; администраторы не затрагиваются."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Отвечает USER_BLOCKED и прерывает обработку."""
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


def _flag(value: bool) -> str:
    """Да/нет из texts.py."""
    return ADMIN_FLAG_YES if value else ADMIN_FLAG_NO


def format_client_card(user: User, referral_count: int) -> str:
    """Карточка клиента для админа."""
    username = user.username or ADMIN_ADMIN_NO_USERNAME
    return ADMIN_CLIENT_CARD.format(
        full_name=html.escape(user.full_name, quote=False),
        tg_id=user.tg_id,
        username=html.escape(username, quote=False),
        phone=html.escape(user.phone or PROFILE_NO_PHONE, quote=False),
        visits_count=user.visits_count,
        referral_count=referral_count,
        discount_10=_flag(user.discount_10_active),
        free_diagnostics=_flag(user.free_diagnostics),
        loyalty_2nd=_flag(user.loyalty_discount_2nd),
    )


async def clients_total(session: AsyncSession) -> int:
    """Общее число пользователей."""
    result = await session.scalar(select(func.count()).select_from(User))
    return int(result or 0)


async def render_clients_page(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    page: int,
) -> None:
    """Страница списка клиентов."""
    total = await clients_total(session)
    if total == 0:
        await state.clear()
        await message.answer(ADMIN_CLIENTS_EMPTY, reply_markup=admin_menu_kb())
        return
    total_pages = max(1, ceil(total / PAGE_SIZE))
    current = min(max(page, 1), total_pages)
    offset = (current - 1) * PAGE_SIZE
    users = await UserRepo.list_clients(session, offset, PAGE_SIZE)
    await state.set_state(AdminPickStates.clients)
    await state.update_data(cli_page=current, cli_total=total_pages)
    labels = [numbered_label(item.id, item.full_name) for item in users]
    await message.answer(
        ADMIN_CLIENTS_HEADER.format(page=current),
        reply_markup=list_kb(labels, page=current, total_pages=total_pages, extra=[BTN_SEARCH]),
    )


async def send_client_card(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    """Карточка одного клиента с действиями."""
    referral_count = await UserRepo.get_referral_count(session, user.id)
    bonuses = get_active_bonuses(user)
    card = format_client_card(user, referral_count)
    if bonuses:
        card = f"{card}\n\n" + "\n".join(bonuses)
    await state.set_state(AdminPickStates.client_card)
    await state.update_data(target_user_id=user.id)
    await message.answer(card, reply_markup=client_card_kb(is_blocked=user.is_blocked))


def settings_text() -> str:
    """Текущие настройки сервиса."""
    return ADMIN_SETTINGS_TEXT.format(
        service_name=settings.service_name,
        phone=settings.service_phone,
        address=settings.service_address,
        hours=settings.service_hours,
        tz=settings.tz,
        bot_username=settings.bot_username,
    )


@router.message(F.text == ADMIN_MENU_BUTTONS["clients"])
async def clients_root(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Пагинированный список клиентов."""
    await render_clients_page(message, state, session, 1)


@router.message(AdminPickStates.clients, F.text == BTN_BACK)
@router.message(AdminPickStates.client_card, F.text == BTN_BACK)
async def clients_back(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Назад: из карточки к списку, из списка в меню."""
    current = await state.get_state()
    if current == AdminPickStates.client_card.state:
        data = await state.get_data()
        await render_clients_page(message, state, session, int(data.get("cli_page", 1)))
        return
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminPickStates.clients, F.text == BTN_PAGE_NEXT)
async def clients_next(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Следующая страница клиентов."""
    data = await state.get_data()
    await render_clients_page(message, state, session, int(data.get("cli_page", 1)) + 1)


@router.message(AdminPickStates.clients, F.text == BTN_PAGE_PREV)
async def clients_prev(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Предыдущая страница клиентов."""
    data = await state.get_data()
    await render_clients_page(message, state, session, int(data.get("cli_page", 1)) - 1)


@router.message(AdminPickStates.clients, F.text == BTN_SEARCH)
async def clients_search_start(message: Message, state: FSMContext) -> None:
    """Запрашивает строку поиска."""
    await state.set_state(AdminSearchStates.enter_query)
    await message.answer(ADMIN_CLIENT_SEARCH_PROMPT, reply_markup=cancel_kb())


@router.message(AdminSearchStates.enter_query, F.text == BTN_CANCEL)
async def clients_search_cancel(message: Message, state: FSMContext) -> None:
    """Отмена поиска."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminSearchStates.enter_query, F.text)
async def clients_search_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Ищет клиентов и показывает кнопки результатов."""
    query = (message.text or "").strip()
    users = await UserRepo.search_clients(session, query)
    if not users:
        await state.clear()
        await message.answer(
            ADMIN_CLIENT_NOT_FOUND.format(query=html.escape(query, quote=False)),
            reply_markup=admin_menu_kb(),
        )
        return
    await state.set_state(AdminPickStates.clients)
    await state.update_data(cli_page=1, cli_total=1)
    labels = [numbered_label(item.id, item.full_name) for item in users[:20]]
    await message.answer(
        ADMIN_CLIENTS_HEADER.format(page=1),
        reply_markup=list_kb(labels, extra=[BTN_SEARCH]),
    )


@router.message(AdminPickStates.clients, F.text.regexp(r"^№\d+"))
async def client_open(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Открывает карточку клиента."""
    user_id = parse_numbered(message.text or "")
    if user_id is None:
        return
    user = await session.get(User, user_id)
    if user is None:
        await message.answer(ADMIN_CLIENT_NOT_FOUND.format(query=str(user_id)))
        return
    await send_client_card(message, state, session, user)


@router.message(AdminPickStates.client_card, F.text == BTN_WRITE)
async def client_write_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Письмо клиенту вне заявки."""
    data = await state.get_data()
    user = await session.get(User, int(data["target_user_id"]))
    if user is None:
        await message.answer(ADMIN_CLIENT_NOT_FOUND.format(query=""))
        return
    await state.set_state(AdminReplyStates.enter_reply)
    await state.update_data(mode="direct", target_user_id=user.id)
    await message.answer(ADMIN_REPLY_PROMPT.format(id=user.tg_id), reply_markup=cancel_kb())


@router.message(AdminReplyStates.enter_reply, FsmModeFilter("direct"), F.text == BTN_CANCEL)
async def client_write_cancel(message: Message, state: FSMContext) -> None:
    """Отмена личного сообщения."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminReplyStates.enter_reply, FsmModeFilter("direct"), F.text)
async def client_write_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отправляет произвольное сообщение клиенту."""
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
        await message.answer(ADMIN_CLIENT_NOT_FOUND.format(query=""), reply_markup=admin_menu_kb())
        return
    await notify_user(message.bot, user.tg_id, text, session=session)
    await message.answer(ADMIN_REPLY_SENT, reply_markup=admin_menu_kb())


@router.message(AdminPickStates.client_card, F.text == BTN_GIFT)
async def client_bonus_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Запрашивает текст подарка."""
    data = await state.get_data()
    user = await session.get(User, int(data["target_user_id"]))
    if user is None:
        await message.answer(ADMIN_CLIENT_NOT_FOUND.format(query=""))
        return
    await state.set_state(AdminBonusStates.enter_bonus_text)
    await state.update_data(target_user_id=user.id)
    await message.answer(ADMIN_REPLY_PROMPT.format(id=user.tg_id), reply_markup=cancel_kb())


@router.message(AdminBonusStates.enter_bonus_text, F.text == BTN_CANCEL)
async def client_bonus_cancel(message: Message, state: FSMContext) -> None:
    """Отмена выдачи бонуса."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminBonusStates.enter_bonus_text, F.text)
async def client_bonus_send(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отправляет клиенту текст подарка."""
    if message.bot is None:
        return
    bonus = (message.text or "").strip()
    if not bonus:
        await message.answer(ADMIN_REPLY_EMPTY, reply_markup=cancel_kb())
        return
    data = await state.get_data()
    user = await session.get(User, int(data["target_user_id"]))
    await state.clear()
    if user is None:
        await message.answer(ADMIN_CLIENT_NOT_FOUND.format(query=""), reply_markup=admin_menu_kb())
        return
    text = ADMIN_GIFT_TO_CLIENT.format(service_name=settings.service_name, text=bonus)
    await notify_user(message.bot, user.tg_id, text, session=session)
    await message.answer(ADMIN_REPLY_SENT, reply_markup=admin_menu_kb())


@router.message(AdminPickStates.client_card, F.text.in_({BTN_BLOCK, BTN_UNBLOCK}))
async def client_toggle_block(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Блокирует или разблокирует клиента."""
    data = await state.get_data()
    user = await session.get(User, int(data["target_user_id"]))
    if user is None:
        await message.answer(ADMIN_CLIENT_NOT_FOUND.format(query=""))
        return
    user.is_blocked = message.text == BTN_BLOCK
    await session.flush()
    await send_client_card(message, state, session, user)


@router.message(F.text == ADMIN_MENU_BUTTONS["settings"])
async def settings_root(message: Message, state: FSMContext) -> None:
    """Показывает текущие настройки сервиса."""
    await state.set_state(AdminPickStates.settings)
    await message.answer(settings_text(), reply_markup=settings_kb(accepting=accepting_requests))


@router.message(AdminPickStates.settings, F.text == BTN_BACK)
async def settings_back(message: Message, state: FSMContext) -> None:
    """Назад в админ-меню."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminPickStates.settings, F.text.in_({BTN_ACCEPT_ON, BTN_ACCEPT_OFF}))
async def settings_toggle_accept(message: Message, state: FSMContext) -> None:
    """Переключает приём новых заявок в памяти процесса."""
    global accepting_requests
    accepting_requests = not accepting_requests
    await message.answer(settings_text(), reply_markup=settings_kb(accepting=accepting_requests))


@router.message(F.text == ADMIN_BTN_TO_CLIENT)
async def back_to_client_menu(message: Message, state: FSMContext) -> None:
    """Возвращает администратора в клиентское меню."""
    await state.clear()
    await message.answer(MENU_MAIN, reply_markup=main_menu_kb())


@router.message(F.text == ADMIN_MENU_BUTTONS["admins"])
async def admins_denied_for_non_owner(message: Message) -> None:
    """Не-владелец нажал «Админы»: прав недостаточно."""
    await message.answer(ADMIN_ACCESS_DENIED, reply_markup=admin_menu_kb())
