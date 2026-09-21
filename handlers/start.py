"""Регистрация, /start и общая навигация."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    User as TgUser,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from database.repo import RequestRepo, UserRepo
from handlers.referral import apply_referral, parse_ref_code
from keyboards.inline import admin_menu_kb, main_menu_kb, webapp_info, webapp_to_url_markup
from texts import (
    ADMIN_MENU,
    LOYALTY_INVITER_REWARD,
    START_GREETING,
    USER_BLOCKED,
)

logger = logging.getLogger(__name__)

router = Router(name="start")


def menu_kb(user: User) -> InlineKeyboardMarkup:
    """Клиентское меню; у администратора есть вход в панель."""
    return main_menu_kb(is_admin=user.is_admin)


def unpack_event(
    event: Message | CallbackQuery,
) -> tuple[Message | None, TgUser | None]:
    """Сообщение и пользователь без ответа Telegram."""
    if isinstance(event, CallbackQuery):
        message = event.message if isinstance(event.message, Message) else None
        return message, event.from_user
    return event, event.from_user


async def ack_event(
    event: Message | CallbackQuery,
) -> tuple[Message | None, TgUser | None]:
    """Для callback отвечает Telegram и возвращает сообщение + пользователя."""
    if isinstance(event, CallbackQuery):
        await event.answer()
    return unpack_event(event)


def _is_button_type_invalid(exc: TelegramBadRequest) -> bool:
    """Telegram отклонил тип кнопки (часто WebApp без /setdomain)."""
    return "button_type_invalid" in str(exc).lower()


async def _send_or_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None,
    *,
    edit: bool,
) -> Message:
    """Отправляет или правит сообщение; WebApp-кнопки при отказе заменяются ссылкой."""
    try:
        if edit:
            return await message.edit_text(text, reply_markup=reply_markup)
        return await message.answer(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return message
        if _is_button_type_invalid(exc) and isinstance(reply_markup, InlineKeyboardMarkup):
            fallback = webapp_to_url_markup(reply_markup)
            if fallback is not reply_markup:
                logger.warning(
                    "Telegram отклонил WebApp-кнопку. "
                    "Привяжите домен Mini App к боту в BotFather (/setdomain). "
                    "Повтор со ссылкой."
                )
                return await _send_or_edit(message, text, fallback, edit=edit)
        if edit:
            return await _send_or_edit(message, text, reply_markup, edit=False)
        raise


async def show_screen(
    event: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None = None,
) -> Message | None:
    """При нажатии inline-кнопки редактирует текущее сообщение, иначе отправляет новое."""
    if isinstance(event, CallbackQuery):
        message = event.message if isinstance(event.message, Message) else None
        if message is None:
            return None
        if isinstance(reply_markup, (ReplyKeyboardMarkup, ReplyKeyboardRemove)):
            return await message.answer(text, reply_markup=reply_markup)
        return await _send_or_edit(message, text, reply_markup, edit=True)
    return await _send_or_edit(event, text, reply_markup, edit=False)


async def safe_send(
    bot: Bot,
    chat_id: int,
    text: str,
    **kwargs: Any,
) -> bool:
    """Отправляет сообщение; ошибки доставки только логируются."""
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramAPIError:
        logger.warning("Не удалось отправить сообщение chat_id=%s", chat_id, exc_info=True)
        return False
    return True


def _display_name(tg_user: TgUser) -> str:
    """Собирает отображаемое имя из данных Telegram."""
    name = (tg_user.full_name or "").strip()
    if name:
        return name
    if tg_user.username:
        return tg_user.username
    return str(tg_user.id)


def _should_be_admin(tg_id: int) -> bool:
    """Владелец и ID из настроек всегда получают флаг администратора."""
    return tg_id == settings.owner_id or tg_id in settings.admin_ids


async def get_or_create_user(session: AsyncSession, tg_user: TgUser) -> tuple[User, bool]:
    """Возвращает пользователя и признак, что запись только что создана."""
    user = await UserRepo.get_by_tg_id(session, tg_user.id)
    created = False
    if user is None:
        user = await UserRepo.create(
            session,
            tg_id=tg_user.id,
            full_name=_display_name(tg_user),
            username=tg_user.username,
            is_admin=_should_be_admin(tg_user.id),
        )
        created = True
    else:
        user.full_name = _display_name(tg_user)
        user.username = tg_user.username
        if _should_be_admin(tg_user.id):
            user.is_admin = True
        await session.flush()
    return user, created


async def require_client(
    event: Message | CallbackQuery,
    session: AsyncSession,
    tg_user: TgUser,
) -> User | None:
    """Клиент без блокировки. Телефон на входе не требуется."""
    user, _created = await get_or_create_user(session, tg_user)
    if user.is_blocked:
        await show_screen(event, USER_BLOCKED.format(phone=settings.service_phone))
        return None
    return user


def start_text() -> str:
    """Приветствие главного экрана."""
    return START_GREETING.format(service_name=settings.service_name)


async def send_main_screen(event: Message | CallbackQuery, user: User) -> None:
    """Показывает клиентское меню."""
    await show_screen(event, start_text(), menu_kb(user))


async def admin_home_kb(session: AsyncSession) -> InlineKeyboardMarkup:
    """Админ-меню с актуальным числом новых заявок."""
    return admin_menu_kb(new_count=await RequestRepo.count_new(session))


async def show_admin_home(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Корень админ-панели."""
    await show_screen(
        event,
        ADMIN_MENU.format(service_name=settings.service_name),
        await admin_home_kb(session),
    )


async def answer_with_menu(
    event: Message | CallbackQuery,
    user: User,
    text: str,
) -> None:
    """Ответ клиенту с главным меню."""
    await show_screen(event, text, menu_kb(user))


async def setup_menu_button(bot: Bot) -> None:
    """Системная кнопка меню слева от поля ввода открывает Mini App."""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Записаться", web_app=webapp_info())
        )
    except TelegramAPIError:
        logger.warning("Не удалось установить Menu Button WebApp", exc_info=True)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Регистрирует пользователя, обрабатывает реферал и показывает витрину."""
    if message.from_user is None:
        return
    await state.clear()
    ref_code = parse_ref_code(command.args)

    user, created = await get_or_create_user(session, message.from_user)
    if created and ref_code is not None:
        outcome = await apply_referral(session, user, ref_code)
        if outcome.client_message:
            await message.answer(outcome.client_message)
        if outcome.referrer is not None:
            await safe_send(bot, outcome.referrer.tg_id, LOYALTY_INVITER_REWARD)

    if user.is_blocked:
        await message.answer(USER_BLOCKED.format(phone=settings.service_phone))
        return
    await send_main_screen(message, user)
