"""FSM-состояния клиентских сценариев."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class QuickBookingStates(StatesGroup):
    """Экспресс-запись: телефон и необязательный комментарий."""

    enter_phone = State()
    enter_note = State()


class QuestionStates(StatesGroup):
    """Вопрос мастеру: текст, фото или аудио + подтверждение."""

    enter_text = State()
    confirm = State()


class MiniAppTicketStates(StatesGroup):
    """Вопрос мастерам по заявке из чек-тикета Mini App."""

    contact_master = State()


class BookingStates(StatesGroup):
    """Совместимость: запись через Mini App без шагов FSM."""


class PriceStates(StatesGroup):
    """Совместимость: расчёт стоимости в Mini App."""


class ProfileStates(StatesGroup):
    """Профиль открывается кнопками, шагов FSM нет."""
