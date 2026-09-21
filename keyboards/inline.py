"""Inline-клавиатуры и фабрики callback_data."""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from database.models import Promo, Service, ServiceCategory, User
from texts import (
    ADMIN_MENU_BUTTONS,
    BONUSES_PROMO_UNLIMITED,
    BTN_ADD_SERVICE,
    BTN_BACK,
    BTN_CALL_NUMBER,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_LAUNCH_BROADCAST,
    BTN_MAIN_MENU,
    BTN_PROCESSED,
    BTN_SEND_MASTER,
    BTN_SHARE_REF,
    BTN_SKIP,
    BTN_WEBAPP_BONUS,
    BTN_WRITE,
    CONTACTS_MAPS_BUTTON,
    CONTACTS_PHONE_BUTTON,
    MENU_BUTTONS,
    WEBAPP_CATEGORY_ORDER,
)
from utils.validators import normalize_phone

NEW_ITEM_ID = 0
NEW_ITEM_CATEGORY = "new"


class ServiceCB(CallbackData, prefix="svc"):
    """Выбор категории услуги."""

    action: str
    value: str


class RequestCB(CallbackData, prefix="req"):
    """Действия по заявке: open / confirm / reply / close."""

    action: str
    request_id: int


class ClientCB(CallbackData, prefix="cli"):
    """Карточка клиента."""

    action: str
    user_id: int


class AdminCB(CallbackData, prefix="adm"):
    """Управление администраторами."""

    action: str
    user_id: int


class ServiceAdminCB(CallbackData, prefix="sva"):
    """Управление услугами прайса."""

    action: str
    service_id: int
    category: str


class PromoAdminCB(CallbackData, prefix="prm"):
    """Управление промо-акциями."""

    action: str
    promo_id: int


class ConfirmCB(CallbackData, prefix="cnf"):
    """Подтверждение шага FSM."""

    action: str


class NavCB(CallbackData, prefix="nav"):
    """Навигация: back / bonuses."""

    action: str


class MenuCB(CallbackData, prefix="menu"):
    """Пункты меню, отмена и пропуск."""

    action: str


class PageCB(CallbackData, prefix="pg"):
    """Постраничная навигация."""

    section: str
    page: int


class BroadcastCB(CallbackData, prefix="bc"):
    """Подтверждение рассылки."""

    action: str


def webapp_info() -> WebAppInfo:
    """URL Mini App."""
    return WebAppInfo(url=settings.webapp_url)


def webapp_button(text: str) -> InlineKeyboardButton:
    """Кнопка открытия Mini App."""
    return InlineKeyboardButton(text=text, web_app=webapp_info())


def webapp_to_url_markup(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Заменяет WebApp-кнопки обычными HTTPS-ссылками.

    Telegram отвечает ``BUTTON_TYPE_INVALID``, если домен Mini App не привязан
    к боту в BotFather или кнопка отправляется не в личный чат.
    """
    new_rows: list[list[InlineKeyboardButton]] = []
    changed = False
    for row in markup.inline_keyboard:
        new_row: list[InlineKeyboardButton] = []
        for button in row:
            if button.web_app is not None:
                new_row.append(InlineKeyboardButton(text=button.text, url=button.web_app.url))
                changed = True
            else:
                new_row.append(button)
        new_rows.append(new_row)
    if not changed:
        return markup
    return InlineKeyboardMarkup(inline_keyboard=new_rows)


def main_menu_kb(*, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню клиента: WebApp + сценарии чата."""
    builder = InlineKeyboardBuilder()
    builder.row(webapp_button(MENU_BUTTONS["webapp"]))
    builder.row(
        InlineKeyboardButton(
            text=MENU_BUTTONS["quick"],
            callback_data=MenuCB(action="quick").pack(),
        ),
        InlineKeyboardButton(
            text=MENU_BUTTONS["bonuses"],
            callback_data=MenuCB(action="bonuses").pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=MENU_BUTTONS["contacts"],
            callback_data=MenuCB(action="contacts").pack(),
        ),
        InlineKeyboardButton(
            text=MENU_BUTTONS["question"],
            callback_data=MenuCB(action="question").pack(),
        ),
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(
                text=MENU_BUTTONS["admin"],
                callback_data=MenuCB(action="admin").pack(),
            )
        )
    return builder.as_markup()


def admin_menu_kb(*, new_count: int = 0) -> InlineKeyboardMarkup:
    """Админ-панель с счётчиком новых заявок."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{ADMIN_MENU_BUTTONS['requests']} ({new_count})",
        callback_data=MenuCB(action="admin_requests"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["dialogs"],
        callback_data=MenuCB(action="admin_dialogs"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["clients"],
        callback_data=MenuCB(action="admin_clients"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["broadcast"],
        callback_data=MenuCB(action="admin_broadcast"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["services"],
        callback_data=MenuCB(action="admin_services"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["promos"],
        callback_data=MenuCB(action="admin_promo"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["stats"],
        callback_data=MenuCB(action="admin_stats"),
    )
    builder.button(
        text=ADMIN_MENU_BUTTONS["exit"],
        callback_data=MenuCB(action="admin_exit"),
    )
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение или отмена."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_CONFIRM, callback_data=ConfirmCB(action="yes"))
    builder.button(text=BTN_CANCEL, callback_data=ConfirmCB(action="no"))
    builder.adjust(2)
    return builder.as_markup()


def question_confirm_kb() -> InlineKeyboardMarkup:
    """Отправка вопроса мастеру."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_SEND_MASTER, callback_data=ConfirmCB(action="yes"))
    builder.button(text=BTN_CANCEL, callback_data=ConfirmCB(action="no"))
    builder.adjust(2)
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    """Отмена текущего шага."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_CANCEL, callback_data=MenuCB(action="cancel"))
    return builder.as_markup()


def skip_cancel_kb() -> InlineKeyboardMarkup:
    """Пропуск или отмена."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_SKIP, callback_data=MenuCB(action="skip"))
    builder.button(text=BTN_CANCEL, callback_data=MenuCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def bonuses_kb(invite_text: str) -> InlineKeyboardMarkup:
    """Бонусы: Mini App, шаринг ссылки, меню."""
    builder = InlineKeyboardBuilder()
    builder.row(webapp_button(BTN_WEBAPP_BONUS))
    builder.row(
        InlineKeyboardButton(
            text=BTN_SHARE_REF,
            switch_inline_query=invite_text,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=BTN_MAIN_MENU,
            callback_data=NavCB(action="back").pack(),
        )
    )
    return builder.as_markup()


def contacts_kb() -> InlineKeyboardMarkup:
    """Карта, звонок (копирование номера) и меню.

    Telegram отклоняет ``tel:`` в inline URL, поэтому номер копируется.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=CONTACTS_MAPS_BUTTON, url=settings.service_maps_url)
    builder.button(
        text=CONTACTS_PHONE_BUTTON,
        copy_text=CopyTextButton(text=settings.service_phone),
    )
    builder.button(text=BTN_MAIN_MENU, callback_data=NavCB(action="back"))
    builder.adjust(1)
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Возврат в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_MAIN_MENU, callback_data=NavCB(action="back"))
    return builder.as_markup()


def client_dialog_kb(request_id: int) -> InlineKeyboardMarkup:
    """Ответ мастеру или закрытие вопроса."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💬 Ответить мастеру",
        callback_data=RequestCB(action="reply", request_id=request_id),
    )
    builder.button(
        text="🔒 Вопрос решён",
        callback_data=RequestCB(action="close", request_id=request_id),
    )
    builder.adjust(2)
    return builder.as_markup()


def admin_request_actions_kb(
    request_id: int,
    *,
    slot: str | None = None,
    phone: str | None = None,
    source: str = "miniapp",
) -> InlineKeyboardMarkup:
    """Кнопки под карточкой заявки в админ-чате: набрать, написать, обработано."""
    del slot, source
    builder = InlineKeyboardBuilder()
    if phone:
        builder.button(
            text=BTN_CALL_NUMBER,
            copy_text=CopyTextButton(text=normalize_phone(phone) or phone),
        )
    builder.button(
        text=BTN_WRITE,
        callback_data=RequestCB(action="reply", request_id=request_id),
    )
    builder.button(
        text=BTN_PROCESSED,
        callback_data=RequestCB(action="close", request_id=request_id),
    )
    builder.adjust(3 if phone else 2)
    return builder.as_markup()


def admin_request_detail_kb(
    request_id: int,
    *,
    slot: str | None = None,
    phone: str | None = None,
) -> InlineKeyboardMarkup:
    """Те же действия на открытой карточке заявки."""
    return admin_request_actions_kb(request_id, slot=slot, phone=phone)


def requests_list_kb(
    items: Sequence[tuple[int, str]],
    section: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Список заявок: кнопка на карточку + пагинация."""
    builder = InlineKeyboardBuilder()
    for request_id, title in items:
        builder.row(
            InlineKeyboardButton(
                text=title[:64],
                callback_data=RequestCB(action="open", request_id=request_id).pack(),
            )
        )
    if total_pages > 1:
        builder.attach(
            InlineKeyboardBuilder.from_markup(pagination_kb(section, page, total_pages))
        )
    return builder.as_markup()


def categories_admin_kb() -> InlineKeyboardMarkup:
    """Категории услуг для WebApp."""
    builder = InlineKeyboardBuilder()
    for value in WEBAPP_CATEGORY_ORDER:
        category = ServiceCategory(value)
        builder.button(
            text=category.label(),
            callback_data=ServiceAdminCB(
                action="cat",
                service_id=NEW_ITEM_ID,
                category=value,
            ),
        )
    builder.button(text=BTN_CANCEL, callback_data=MenuCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def _short(text: str, limit: int = 28) -> str:
    """Обрезает подпись кнопки."""
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def services_list_kb(services: Sequence[Service]) -> InlineKeyboardMarkup:
    """Список услуг: правка цены, скрыть/показать, удалить."""
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
            text=BTN_ADD_SERVICE,
            callback_data=ServiceAdminCB(
                action="add",
                service_id=NEW_ITEM_ID,
                category=NEW_ITEM_CATEGORY,
            ).pack(),
        )
    )
    return builder.as_markup()


def promos_list_kb(promos: Sequence[Promo]) -> InlineKeyboardMarkup:
    """Список акций."""
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
    """Список администраторов (владелец)."""
    builder = InlineKeyboardBuilder()
    for admin in admins:
        username = f"@{admin.username}" if admin.username else str(admin.tg_id)
        title = f"{_short(admin.full_name)} · {username}"
        prefix = "⭐ " if admin.tg_id == settings.owner_id else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{prefix}{title}",
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
        text="✍️ Личное сообщение",
        callback_data=ClientCB(action="write", user_id=user_id),
    )
    builder.button(
        text="🎁 Начислить бонусы",
        callback_data=ClientCB(action="bonus", user_id=user_id),
    )
    builder.button(
        text="✅ Разблокировать" if is_blocked else "🚫 Заблокировать",
        callback_data=ClientCB(
            action="unblock" if is_blocked else "block",
            user_id=user_id,
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Запуск рассылки."""
    builder = InlineKeyboardBuilder()
    builder.button(text=BTN_LAUNCH_BROADCAST, callback_data=BroadcastCB(action="send"))
    builder.button(text=BTN_CANCEL, callback_data=BroadcastCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def pagination_kb(prefix: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Пагинация: «Назад / Стр N/M / Вперед»."""
    safe_total = max(total_pages, 1)
    current = min(max(page, 1), safe_total)
    builder = InlineKeyboardBuilder()
    if current > 1:
        builder.button(
            text="⬅️ Назад",
            callback_data=PageCB(section=prefix, page=current - 1),
        )
    builder.button(
        text=f"Стр {current}/{safe_total}",
        callback_data=PageCB(section=prefix, page=current),
    )
    if current < safe_total:
        builder.button(
            text="Вперед ➡️",
            callback_data=PageCB(section=prefix, page=current + 1),
        )
    builder.adjust(3)
    return builder.as_markup()


def service_categories_kb() -> InlineKeyboardMarkup:
    """Категории для клиентских сценариев (если понадобятся в чате)."""
    builder = InlineKeyboardBuilder()
    for value in WEBAPP_CATEGORY_ORDER:
        category = ServiceCategory(value)
        builder.button(
            text=category.label(),
            callback_data=ServiceCB(action="choose", value=value),
        )
    builder.button(text=BTN_CANCEL, callback_data=MenuCB(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    """Совместимость: бонусы открываются из главного меню."""
    return bonuses_kb("")
