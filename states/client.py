"""FSM-состояния клиентских сценариев."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Запись на обслуживание."""

    choose_service = State()
    enter_problem = State()
    enter_car = State()
    confirm = State()


class PriceStates(StatesGroup):
    """Запрос ориентировочной стоимости."""

    choose_service = State()
    enter_car = State()
    confirm = State()


class QuestionStates(StatesGroup):
    """Свободный вопрос мастеру."""

    enter_text = State()
    confirm = State()


class ProfileStates(StatesGroup):
    """Профиль открывается кнопками, шагов FSM нет."""
