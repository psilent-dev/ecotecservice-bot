"""Команды /admin, /cancel и вход в панель с клиентского меню."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.repo import UserRepo
from handlers.start import ack_event, menu_kb, show_admin_home, show_screen
from keyboards.inline import MenuCB
from texts import ADMIN_ACCESS_DENIED, FSM_CANCELLED

router = Router(name="admin_entry")


class FsmModeFilter(BaseFilter):
    """Сравнивает поле `mode` в данных FSM с ожидаемым значением."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def __call__(self, event: TelegramObject, state: FSMContext) -> bool:
        """True, если в FSM записан нужный режим."""
        data = await state.get_data()
        return data.get("mode") == self.mode


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    """Открывает админ-панель."""
    if message.from_user is None:
        return
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    if user is None or not user.is_admin:
        await message.answer(ADMIN_ACCESS_DENIED)
        return
    await show_admin_home(message, session)


@router.callback_query(MenuCB.filter(F.action == "admin"))
async def open_admin_from_menu(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Кнопка «Панель управления» в клиентском меню."""
    await callback.answer()
    if callback.from_user is None:
        return
    user = await UserRepo.get_by_tg_id(session, callback.from_user.id)
    if user is None or not user.is_admin:
        await show_screen(callback, ADMIN_ACCESS_DENIED)
        return
    await show_admin_home(callback, session)


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сбрасывает любой FSM и возвращает в клиентское меню."""
    if message.from_user is None:
        return
    await state.clear()
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    if user is None:
        await message.answer(FSM_CANCELLED)
        return
    await show_screen(message, FSM_CANCELLED, menu_kb(user))
