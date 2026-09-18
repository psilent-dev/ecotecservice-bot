"""Inline-клавиатуры и фабрики callback_data."""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from database.models import Promo, Service, ServiceCategory, User
from texts import (
    BONUSES_PROMO_UNLIMITED,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_MAIN_MENU,
    CONTACTS_MAPS_BUTTON,
    CONTACTS_PHONE_BUTTON,
)

# Идентификатор-заглушка в CallbackData, когда запись ещё не выбрана (кнопка «добавить»).
NEW_ITEM_ID = 0
NEW_ITEM_CATEGORY = "new"


class ServiceCB(CallbackData, prefix="svc"):
    """Выбор категории услуги клиентом."""

    action: str
    value: str


class RequestCB(CallbackData, prefix="req"):
    """Действия администратора по заявке: reply / close / reopen."""

    action: str
    request_id: int


class ClientCB(CallbackData, prefix="cli"):
    """Карточка клиента: write / bonus / block / unblock."""

    action: str
    user_id: int


class AdminCB(CallbackData, prefix="adm"):
    """Управление администраторами: add / remove."""

    action: str
    user_id: int


class ServiceAdminCB(CallbackData, prefix="sva"):
    """Управление услугами прайса: edit / delete / toggle / add."""

    action: str
    service_id: int
    category: str


class PromoAdminCB(CallbackData, prefix="prm"):
    """Управление промо-акциями: edit / delete / toggle / add."""

    action: str
    promo_id: int


class ConfirmCB(CallbackData, prefix="cnf"):
    """Подтверждение или отмена шага FSM (yes / no)."""

    action: str


class NavCB(CallbackData, prefix="nav"):
    """Навигация клиента: back / bonuses."""

    action: str


class PageCB(CallbackData, prefix="pg"):
    """Постраничная навигация списков."""

    section: str
    page: int


class BroadcastCB(CallbackData, prefix="bc"):
    """Подтверждение рассылки: send / cancel."""

    action: str


def service_categories_kb() -> InlineKeyboardMarkup:
    """Семь категорий услуг автосервиса."""
    builder = InlineKeyboardBuilder()
    for category in ServiceCategory:
        builder.button(
            text=category.label(),
            callback_data=ServiceCB(action="choose", value=category.value),
        )
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение или отмена текущего шага."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_CONFIRM, callback_data=ConfirmCB(action="yes"))
    builder.button(text=BTN_CANCEL, callback_data=ConfirmCB(action="no"))
    builder.adjust(2)
    return builder.as_markup()


def admin_request_actions_kb(request_id: int) -> InlineKeyboardMarkup:
    """Действия по заявке в админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💬 Ответить",
        callback_data=RequestCB(action="reply", request_id=request_id),
    )
    builder.button(
        text="🔒 Закрыть",
        callback_data=RequestCB(action="close", request_id=request_id),
    )
    builder.button(
        text="↩️ Вернуть в работу",
        callback_data=RequestCB(action="reopen", request_id=request_id),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def client_dialog_kb(request_id: int) -> InlineKeyboardMarkup:
    """Продолжение диалога по уже отвеченной заявке."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💬 Ответить ещё",
        callback_data=RequestCB(action="reply", request_id=request_id),
    )
    builder.button(
        text="🔒 Закрыть",
        callback_data=RequestCB(action="close", request_id=request_id),
    )
    builder.adjust(2)
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    """Кнопка перехода к бонусам из профиля."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎁 Мои бонусы",
        callback_data=NavCB(action="bonuses"),
    )
    return builder.as_markup()


def contacts_kb() -> InlineKeyboardMarkup:
    """Ссылка на карту и кнопка копирования телефона.

    URL ``tel:`` Telegram отклоняет (Wrong port number), поэтому номер
    копируется в буфер через ``CopyTextButton``.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=CONTACTS_MAPS_BUTTON, url=settings.service_maps_url)
    builder.button(
        text=CONTACTS_PHONE_BUTTON,
        copy_text=CopyTextButton(text=settings.service_phone),
    )
    builder.adjust(1)
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Возврат в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_MAIN_MENU, callback_data=NavCB(action="back"))
    return builder.as_markup()


def _short(text: str, limit: int = 28) -> str:
    """Обрезает подпись кнопки до лимита Telegram."""
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def services_list_kb(services: Sequence[Service]) -> InlineKeyboardMarkup:
    """Список услуг с кнопками редактирования, переключения и удаления."""
    builder = InlineKeyboardBuilder()
    for service in services:
        marker = "✅" if service.is_active else "🚫"
        category_value = service.category.value
        builder.row(
            InlineKeyboardButton(
                text=f"{marker} {_short(service.name)}",
                callback_data=ServiceAdminCB(
                    action="edit",
                    service_id=service.id,
                    category=category_value,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🔄",
                callback_data=ServiceAdminCB(
                    action="toggle",
                    service_id=service.id,
                    category=category_value,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=ServiceAdminCB(
                    action="delete",
                    service_id=service.id,
                    category=category_value,
                ).pack(),
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить услугу",
            callback_data=ServiceAdminCB(
                action="add",
                service_id=NEW_ITEM_ID,
                category=NEW_ITEM_CATEGORY,
            ).pack(),
        )
    )
    return builder.as_markup()


def promos_list_kb(promos: Sequence[Promo]) -> InlineKeyboardMarkup:
    """Список акций с кнопками управления."""
    builder = InlineKeyboardBuilder()
    for promo in promos:
        marker = "✅" if promo.is_active else "🚫"
        until = (
            promo.valid_until.strftime("%d.%m.%Y")
            if promo.valid_until is not None
            else BONUSES_PROMO_UNLIMITED
        )
        builder.row(
            InlineKeyboardButton(
                text=f"{marker} {_short(promo.title)} · {until}",
                callback_data=PromoAdminCB(action="edit", promo_id=promo.id).pack(),
            ),
            InlineKeyboardButton(
                text="🔄",
                callback_data=PromoAdminCB(action="toggle", promo_id=promo.id).pack(),
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=PromoAdminCB(action="delete", promo_id=promo.id).pack(),
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить акцию",
            callback_data=PromoAdminCB(action="add", promo_id=NEW_ITEM_ID).pack(),
        )
    )
    return builder.as_markup()


def admins_list_kb(admins: Sequence[User]) -> InlineKeyboardMarkup:
    """Список администраторов с кнопкой снятия и добавления."""
    builder = InlineKeyboardBuilder()
    for admin in admins:
        username = f"@{admin.username}" if admin.username else str(admin.tg_id)
        is_owner = admin.tg_id == settings.owner_id
        title = f"{_short(admin.full_name)} · {username}"
        if is_owner:
            builder.row(
                InlineKeyboardButton(
                    text=f"⭐ {title}",
                    callback_data=AdminCB(action="remove", user_id=admin.id).pack(),
                )
            )
            continue
        builder.row(
            InlineKeyboardButton(
                text=title,
                callback_data=AdminCB(action="remove", user_id=admin.id).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Назначить админа",
            callback_data=AdminCB(action="add", user_id=NEW_ITEM_ID).pack(),
        )
    )
    return builder.as_markup()


def client_card_kb(user_id: int, *, is_blocked: bool) -> InlineKeyboardMarkup:
    """Действия в карточке клиента."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✍️ Написать",
        callback_data=ClientCB(action="write", user_id=user_id),
    )
    builder.button(
        text="🎁 Бонус",
        callback_data=ClientCB(action="bonus", user_id=user_id),
    )
    if is_blocked:
        builder.button(
            text="✅ Разблокировать",
            callback_data=ClientCB(action="unblock", user_id=user_id),
        )
    else:
        builder.button(
            text="🚫 Заблокировать",
            callback_data=ClientCB(action="block", user_id=user_id),
        )
    builder.adjust(2, 1)
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение массовой рассылки."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_CONFIRM, callback_data=BroadcastCB(action="send"))
    builder.button(text=BTN_CANCEL, callback_data=BroadcastCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def pagination_kb(prefix: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Общая пагинация для списков. Страницы нумеруются с 1."""
    safe_total = max(total_pages, 1)
    current = min(max(page, 1), safe_total)
    builder = InlineKeyboardBuilder()
    if current > 1:
        builder.button(
            text="⬅️",
            callback_data=PageCB(section=prefix, page=current - 1),
        )
    builder.button(
        text=f"{current}/{safe_total}",
        callback_data=PageCB(section=prefix, page=current),
    )
    if current < safe_total:
        builder.button(
            text="➡️",
            callback_data=PageCB(section=prefix, page=current + 1),
        )
    builder.adjust(3)
    return builder.as_markup()
