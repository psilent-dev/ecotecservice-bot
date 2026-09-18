"""Регистрация, /start и запрос телефона."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import BaseFilter, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from database.repo import UserRepo
from handlers.referral import apply_referral, parse_ref_code
from keyboards.reply import admin_menu_kb, main_menu_kb, phone_request_kb
from texts import (
    ADMIN_MENU,
    ERROR_PHONE_INVALID,
    LOYALTY_INVITER_REWARD,
    PHONE_RECEIVED,
    SHARE_PHONE_REQUEST,
    START_GREETING,
    USER_BLOCKED,
)
from utils.validators import normalize_phone

logger = logging.getLogger(__name__)

router = Router(name="start")


class WaitingPhoneFilter(BaseFilter):
    """Пропускает текстовый номер, только если у пользователя ещё нет телефона."""

    async def __call__(
        self,
        event: TelegramObject,
        session: AsyncSession,
        event_from_user: TgUser | None = None,
    ) -> bool:
        """True, если это похоже на телефон и в профиле номер ещё не сохранён."""
        if event_from_user is None or not isinstance(event, Message) or event.text is None:
            return False
        if normalize_phone(event.text) is None:
            return False
        user = await UserRepo.get_by_tg_id(session, event_from_user.id)
        return user is None or not user.phone


def menu_kb(user: User) -> ReplyKeyboardMarkup:
    """Reply-клавиатура с учётом прав администратора."""
    if user.is_admin:
        return admin_menu_kb()
    return main_menu_kb()


async def safe_send(
    bot: Bot,
    chat_id: int,
    text: str,
    **kwargs: Any,
) -> bool:
    """Отправляет сообщение; ошибки доставки только логируются."""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except TelegramAPIError:
        logger.warning("Не удалось отправить сообщение chat_id=%s", chat_id, exc_info=True)
        return False


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
    message: Message,
    session: AsyncSession,
    tg_user: TgUser,
) -> User | None:
    """Готовый к работе клиент либо ответ с просьбой о телефоне / блокировке."""
    user, _created = await get_or_create_user(session, tg_user)
    if user.is_blocked:
        await message.answer(USER_BLOCKED.format(phone=settings.service_phone))
        return None
    if not user.phone:
        await message.answer(SHARE_PHONE_REQUEST, reply_markup=phone_request_kb())
        return None
    return user


async def send_main_screen(message: Message, user: User) -> None:
    """Приветствие и меню: у админа клавиатура админ-панели."""
    greeting = START_GREETING.format(service_name=settings.service_name)
    if user.is_admin:
        await message.answer(greeting, reply_markup=main_menu_kb())
        await message.answer(ADMIN_MENU, reply_markup=admin_menu_kb())
        return
    await message.answer(greeting, reply_markup=main_menu_kb())


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    """Регистрирует пользователя, обрабатывает реферальный deep-link и показывает меню."""
    if message.from_user is None:
        return
    await state.clear()
    ref_code = parse_ref_code(command.args)
    if ref_code is not None:
        await state.update_data(ref_code=ref_code)

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
    if not user.phone:
        await message.answer(SHARE_PHONE_REQUEST, reply_markup=phone_request_kb())
        return
    await send_main_screen(message, user)


@router.message(F.contact)
async def handle_contact(message: Message, session: AsyncSession) -> None:
    """Сохраняет телефон из кнопки «поделиться контактом»."""
    if message.from_user is None or message.contact is None:
        return
    contact = message.contact
    if contact.user_id not in (None, 0, message.from_user.id):
        await message.answer(ERROR_PHONE_INVALID, reply_markup=phone_request_kb())
        return
    phone = normalize_phone(contact.phone_number)
    if phone is None:
        await message.answer(ERROR_PHONE_INVALID, reply_markup=phone_request_kb())
        return
    await _save_phone_and_greet(message, session, phone)


@router.message(StateFilter(None), WaitingPhoneFilter())
async def handle_typed_phone(message: Message, session: AsyncSession) -> None:
    """Принимает номер, введённый текстом, если телефона ещё нет."""
    if message.from_user is None or message.text is None:
        return
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    if user is not None and user.phone:
        return
    phone = normalize_phone(message.text)
    if phone is None:
        await message.answer(ERROR_PHONE_INVALID, reply_markup=phone_request_kb())
        return
    await _save_phone_and_greet(message, session, phone)


async def _save_phone_and_greet(
    message: Message,
    session: AsyncSession,
    phone: str,
) -> None:
    """Пишет телефон в профиль и открывает меню."""
    if message.from_user is None:
        return
    user, _created = await get_or_create_user(session, message.from_user)
    if user.is_blocked:
        await message.answer(USER_BLOCKED.format(phone=settings.service_phone))
        return
    await UserRepo.update_phone(session, user.tg_id, phone)
    await session.refresh(user)
    await message.answer(PHONE_RECEIVED)
    await send_main_screen(message, user)


async def answer_with_menu(message: Message, user: User, text: str) -> None:
    """Ответ клиенту с подходящей reply-клавиатурой."""
    await message.answer(text, reply_markup=menu_kb(user))
