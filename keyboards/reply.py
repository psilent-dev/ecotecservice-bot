"""Reply-клавиатуры бота «Экотек Сервис»."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from texts import ADMIN_MENU_BUTTONS, BTN_CANCEL, BTN_SHARE_PHONE, MENU_BUTTONS

ADMIN_BTN_ANSWERED = MENU_BUTTONS["admin_answered"]
ADMIN_BTN_TO_CLIENT = MENU_BUTTONS["admin_exit"]


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню клиента."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=MENU_BUTTONS["booking"]),
        KeyboardButton(text=MENU_BUTTONS["price"]),
    )
    builder.row(
        KeyboardButton(text=MENU_BUTTONS["question"]),
        KeyboardButton(text=MENU_BUTTONS["profile"]),
    )
    builder.row(KeyboardButton(text=MENU_BUTTONS["contacts"]))
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def phone_request_kb() -> ReplyKeyboardMarkup:
    """Кнопка запроса контакта для сохранения телефона."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_SHARE_PHONE, request_contact=True))
    return builder.as_markup(resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню администратора."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=ADMIN_MENU_BUTTONS["requests"]),
        KeyboardButton(text=ADMIN_BTN_ANSWERED),
    )
    builder.row(
        KeyboardButton(text=ADMIN_MENU_BUTTONS["clients"]),
        KeyboardButton(text=ADMIN_MENU_BUTTONS["broadcast"]),
    )
    builder.row(
        KeyboardButton(text=ADMIN_MENU_BUTTONS["services"]),
        KeyboardButton(text=ADMIN_MENU_BUTTONS["promos"]),
    )
    builder.row(
        KeyboardButton(text=ADMIN_MENU_BUTTONS["admins"]),
        KeyboardButton(text=ADMIN_MENU_BUTTONS["settings"]),
    )
    builder.row(KeyboardButton(text=ADMIN_BTN_TO_CLIENT))
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура отмены текущего FSM-шага."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_CANCEL))
    return builder.as_markup(resize_keyboard=True)
