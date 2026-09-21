"""Отправка уведомлений клиентам и администраторам."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.repo import UserRepo

logger = logging.getLogger(__name__)

Keyboard = InlineKeyboardMarkup | ReplyKeyboardMarkup | None


def markup_without_tel(markup: Keyboard) -> Keyboard:
    """Telegram отклоняет ``tel:`` в inline URL — подменяет копированием номера."""
    if not isinstance(markup, InlineKeyboardMarkup):
        return markup
    changed = False
    new_rows: list[list[InlineKeyboardButton]] = []
    for row in markup.inline_keyboard:
        new_row: list[InlineKeyboardButton] = []
        for button in row:
            url = button.url or ""
            if url.startswith("tel:"):
                phone = url.removeprefix("tel:")
                new_row.append(
                    InlineKeyboardButton(text=button.text, copy_text=CopyTextButton(text=phone))
                )
                changed = True
            else:
                new_row.append(button)
        new_rows.append(new_row)
    if not changed:
        return markup
    return InlineKeyboardMarkup(inline_keyboard=new_rows)


async def notify_user(
    bot: Bot,
    tg_id: int,
    text: str,
    reply_markup: Keyboard = None,
    session: AsyncSession | None = None,
) -> bool:
    """Пишет пользователю. При блокировке бота помечает `is_blocked` и не бросает ошибку."""
    try:
        await bot.send_message(tg_id, text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as exc:
        fallback = markup_without_tel(reply_markup)
        if fallback is not reply_markup:
            logger.warning("Telegram отклонил tel: URL, повтор с копированием номера")
            try:
                await bot.send_message(tg_id, text, reply_markup=fallback)
                return True
            except TelegramAPIError:
                logger.warning("Не удалось написать tg_id=%s после fallback", tg_id, exc_info=True)
                return False
        logger.warning("Не удалось написать tg_id=%s: %s", tg_id, exc)
        return False
    except TelegramForbiddenError:
        logger.warning("Пользователь tg_id=%s заблокировал бота", tg_id)
        if session is not None:
            user = await UserRepo.get_by_tg_id(session, tg_id)
            if user is not None:
                user.is_blocked = True
                await session.flush()
        return False
    except TelegramAPIError:
        logger.warning("Не удалось написать tg_id=%s", tg_id, exc_info=True)
        return False


async def notify_admins(
    bot: Bot,
    session: AsyncSession,
    text: str,
    reply_markup: Keyboard = None,
) -> int:
    """Отправляет заявку только в админ-чат `ADMIN_CHAT_ID`, без личных сообщений."""
    chat_id = settings.admin_chat_id
    if chat_id is None:
        logger.error("ADMIN_CHAT_ID не задан — заявка не отправлена в админ-чат")
        return 0
    ok = await notify_user(bot, chat_id, text, reply_markup=reply_markup, session=session)
    return 1 if ok else 0
