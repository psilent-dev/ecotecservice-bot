"""Команды /admin и /cancel."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.repo import UserRepo
from keyboards.reply import admin_menu_kb, main_menu_kb
from texts import ADMIN_ACCESS_DENIED, ADMIN_MENU, FSM_CANCELLED

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
    """Открывает админ-панель или сообщает об отсутствии прав."""
    if message.from_user is None:
        return
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    if user is None or not user.is_admin:
        await message.answer(ADMIN_ACCESS_DENIED)
        return
    await message.answer(ADMIN_MENU, reply_markup=admin_menu_kb())


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сбрасывает любой FSM и возвращает в меню по роли."""
    if message.from_user is None:
        return
    await state.clear()
    user = await UserRepo.get_by_tg_id(session, message.from_user.id)
    if user is not None and user.is_admin:
        await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())
        return
    await message.answer(FSM_CANCELLED, reply_markup=main_menu_kb())
