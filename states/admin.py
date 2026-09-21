"""FSM-состояния административных сценариев."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminReplyStates(StatesGroup):
    """Ответ администратора на заявку клиента."""

    enter_reply = State()


class AdminBroadcastStates(StatesGroup):
    """Массовая рассылка клиентам."""

    enter_text = State()
    confirm = State()


class AdminServiceStates(StatesGroup):
    """Создание и редактирование услуги прайса."""

    choose_category = State()
    enter_name = State()
    enter_description = State()
    enter_price_from = State()
    enter_price_to = State()
    confirm = State()


class AdminPromoStates(StatesGroup):
    """Создание и редактирование промо-акции."""

    enter_title = State()
    enter_description = State()
    enter_discount = State()
    enter_valid_until = State()
    confirm = State()


class AdminSearchStates(StatesGroup):
    """Поиск клиента в админ-панели."""

    enter_query = State()


class AdminAddAdminStates(StatesGroup):
    """Назначение нового администратора по Telegram ID."""

    enter_tg_id = State()
    confirm = State()


class AdminBonusStates(StatesGroup):
    """Ручное начисление бонусов клиенту."""

    enter_amount = State()
