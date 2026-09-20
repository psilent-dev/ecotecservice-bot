"""Reply-клавиатуры бота «Экотек Сервис»."""

from __future__ import annotations

import re
from collections.abc import Sequence

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from database.models import ServiceCategory
from texts import (
    ADMIN_MENU_BUTTONS,
    BTN_ACCEPT_OFF,
    BTN_ACCEPT_ON,
    BTN_ADD,
    BTN_ADD_ADMIN,
    BTN_BACK,
    BTN_BLOCK,
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_CONFIRM,
    BTN_DELETE,
    BTN_EDIT,
    BTN_GIFT,
    BTN_MAIN_MENU,
    BTN_PAGE_NEXT,
    BTN_PAGE_PREV,
    BTN_REOPEN,
    BTN_REPLY,
    BTN_REPLY_AGAIN,
    BTN_SEARCH,
    BTN_SHARE_PHONE,
    BTN_SKIP,
    BTN_TOGGLE,
    BTN_UNBLOCK,
    BTN_WRITE,
    MENU_BUTTONS,
)

ADMIN_BTN_ANSWERED = MENU_BUTTONS["admin_answered"]
ADMIN_BTN_TO_CLIENT = MENU_BUTTONS["admin_exit"]

_NUM_RE = re.compile(r"^№(\d+)\b")
_TRAIL_NUM_RE = re.compile(r"№(\d+)\s*$")


def numbered_label(item_id: int, title: str, limit: int = 40) -> str:
    """Подпись кнопки со встроенным id: «№12 Иванов»."""
    prefix = f"№{item_id} "
    tail = title.strip().replace("\n", " ")
    return prefix + tail[: max(1, limit - len(prefix))]


def parse_numbered(text: str) -> int | None:
    """Достаёт id из начала кнопки «№12 …»."""
    match = _NUM_RE.match((text or "").strip())
    return int(match.group(1)) if match else None


def parse_trailing_num(text: str) -> int | None:
    """Достаёт id с конца кнопки «… №12»."""
    match = _TRAIL_NUM_RE.search((text or "").strip())
    return int(match.group(1)) if match else None


def category_from_label(text: str) -> ServiceCategory | None:
    """Категория услуги по подписи кнопки."""
    for category in ServiceCategory:
        if category.label() == text:
            return category
    return None


def reply_grid(
    labels: Sequence[str],
    *,
    cols: int = 2,
    footer: Sequence[Sequence[str]] | None = None,
) -> ReplyKeyboardMarkup:
    """Сетка reply-кнопок с необязательным нижним рядом."""
    builder = ReplyKeyboardBuilder()
    row: list[KeyboardButton] = []
    for label in labels:
        row.append(KeyboardButton(text=label))
        if len(row) >= cols:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)
    if footer:
        for extra in footer:
            if extra:
                builder.row(*(KeyboardButton(text=item) for item in extra))
    return builder.as_markup(resize_keyboard=True)


def _nav_footer(*, page: int, total_pages: int, extra: Sequence[str] | None = None) -> list[list[str]]:
    """Стрелки пагинации, доп. кнопки и «Назад»."""
    rows: list[list[str]] = []
    arrows: list[str] = []
    if page > 1:
        arrows.append(BTN_PAGE_PREV)
    if page < max(total_pages, 1):
        arrows.append(BTN_PAGE_NEXT)
    if arrows:
        rows.append(arrows)
    if extra:
        rows.append(list(extra))
    rows.append([BTN_BACK])
    return rows


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
    builder.row(
        KeyboardButton(text=MENU_BUTTONS["bonuses"]),
        KeyboardButton(text=MENU_BUTTONS["contacts"]),
    )
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
    return reply_grid([BTN_CANCEL], cols=1)


def confirm_kb() -> ReplyKeyboardMarkup:
    """Подтверждение или отмена шага."""
    return reply_grid([BTN_CONFIRM, BTN_CANCEL], cols=2)


def skip_cancel_kb() -> ReplyKeyboardMarkup:
    """Пропуск необязательного поля или отмена."""
    return reply_grid([BTN_SKIP, BTN_CANCEL], cols=2)


def service_categories_kb(*, with_cancel: bool = True) -> ReplyKeyboardMarkup:
    """Категории услуг reply-кнопками."""
    labels = [item.label() for item in ServiceCategory]
    footer = [[BTN_CANCEL]] if with_cancel else [[BTN_BACK]]
    return reply_grid(labels, cols=2, footer=footer)


def request_actions_kb() -> ReplyKeyboardMarkup:
    """Действия по выбранной заявке."""
    return reply_grid(
        [BTN_REPLY, BTN_CLOSE, BTN_REOPEN],
        cols=2,
        footer=[[BTN_BACK]],
    )


def client_dialog_kb(request_id: int) -> ReplyKeyboardMarkup:
    """Клиент продолжает или закрывает заявку."""
    return reply_grid(
        [
            f"{BTN_REPLY_AGAIN} №{request_id}",
            f"{BTN_CLOSE} №{request_id}",
        ],
        cols=1,
        footer=[[BTN_MAIN_MENU]],
    )


def list_kb(
    labels: Sequence[str],
    *,
    page: int = 1,
    total_pages: int = 1,
    extra: Sequence[str] | None = None,
) -> ReplyKeyboardMarkup:
    """Список элементов с пагинацией и «Назад»."""
    return reply_grid(labels, cols=1, footer=_nav_footer(page=page, total_pages=total_pages, extra=extra))


def service_item_kb() -> ReplyKeyboardMarkup:
    """Действия внутри услуги."""
    return reply_grid(
        [BTN_EDIT, BTN_TOGGLE, BTN_DELETE],
        cols=2,
        footer=[[BTN_BACK]],
    )


def promo_item_kb() -> ReplyKeyboardMarkup:
    """Действия внутри акции."""
    return reply_grid(
        [BTN_EDIT, BTN_TOGGLE, BTN_DELETE],
        cols=2,
        footer=[[BTN_BACK]],
    )


def client_card_kb(*, is_blocked: bool) -> ReplyKeyboardMarkup:
    """Действия в карточке клиента."""
    block = BTN_UNBLOCK if is_blocked else BTN_BLOCK
    return reply_grid(
        [BTN_WRITE, BTN_GIFT, block],
        cols=2,
        footer=[[BTN_BACK]],
    )


def settings_kb(*, accepting: bool) -> ReplyKeyboardMarkup:
    """Переключение приёма заявок."""
    toggle = BTN_ACCEPT_ON if accepting else BTN_ACCEPT_OFF
    return reply_grid([toggle], cols=1, footer=[[BTN_BACK]])
