"""Единственная reply-клавиатура: запрос контакта."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from texts import BTN_SHARE_PHONE


def phone_request_kb() -> ReplyKeyboardMarkup:
    """Кнопка запроса контакта для быстрой записи."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_SHARE_PHONE, request_contact=True))
    return builder.as_markup(resize_keyboard=True)
