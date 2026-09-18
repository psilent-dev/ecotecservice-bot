"""Владелец: назначение и снятие администраторов."""

from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User
from database.repo import UserRepo
from filters.admin import IsOwner
from keyboards.inline import NEW_ITEM_ID, AdminCB, ConfirmCB, admins_list_kb, confirm_kb
from keyboards.reply import admin_menu_kb, cancel_kb
from services.notify import notify_user
from states.admin import AdminAddAdminStates
from texts import (
    ADMIN_NEW_ADMIN_GRANTED,
    ADMIN_ADMIN_ADDED,
    ADMIN_ADMIN_ADD_PROMPT,
    ADMIN_ADMIN_CANNOT_REMOVE_OWNER,
    ADMIN_ADMIN_EXISTS,
    ADMIN_ADMIN_NO_USERNAME,
    ADMIN_ADMIN_NOT_FOUND,
    ADMIN_ADMIN_REMOVED,
    ADMIN_ADMINS_HEADER,
    ADMIN_ADMINS_ITEM,
    ADMIN_INVALID_TG_ID,
    ADMIN_MENU_BUTTONS,
    BTN_CANCEL,
    FSM_CANCELLED,
)
from utils.validators import is_valid_tg_id

router = Router(name="admin_admins")
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())


def format_admin_item(user: User) -> str:
    """Строка администратора для списка."""
    username = user.username or ADMIN_ADMIN_NO_USERNAME
    return ADMIN_ADMINS_ITEM.format(
        full_name=html.escape(user.full_name, quote=False),
        tg_id=user.tg_id,
        username=html.escape(username, quote=False),
    )


async def show_admins(target: Message, session: AsyncSession) -> None:
    """Печатает текущих администраторов."""
    admins = await UserRepo.get_all_admins(session)
    lines = [ADMIN_ADMINS_HEADER]
    lines.extend(format_admin_item(item) for item in admins)
    await target.answer("\n".join(lines), reply_markup=admins_list_kb(admins))


@router.message(F.text == ADMIN_MENU_BUTTONS["admins"])
async def admins_root(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Корень раздела администраторов. Только владелец."""
    await state.clear()
    await show_admins(message, session)


@router.callback_query(AdminCB.filter(F.action == "add"))
async def admin_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрашивает Telegram ID нового администратора."""
    await callback.answer()
    await state.set_state(AdminAddAdminStates.enter_tg_id)
    if callback.message:
        await callback.message.answer(ADMIN_ADMIN_ADD_PROMPT, reply_markup=cancel_kb())


@router.message(AdminAddAdminStates.enter_tg_id, F.text == BTN_CANCEL)
@router.message(AdminAddAdminStates.confirm, F.text == BTN_CANCEL)
async def admin_add_cancel(message: Message, state: FSMContext) -> None:
    """Отмена назначения администратора."""
    await state.clear()
    await message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.message(AdminAddAdminStates.enter_tg_id, F.text)
async def admin_enter_tg_id(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Проверяет, что пользователь с таким tg_id уже есть в базе."""
    raw = (message.text or "").strip()
    if not is_valid_tg_id(raw):
        await message.answer(ADMIN_INVALID_TG_ID, reply_markup=cancel_kb())
        return
    tg_id = int(raw)
    user = await UserRepo.get_by_tg_id(session, tg_id)
    if user is None:
        await message.answer(ADMIN_ADMIN_NOT_FOUND.format(tg_id=tg_id), reply_markup=cancel_kb())
        return
    if user.is_admin:
        await state.clear()
        await message.answer(ADMIN_ADMIN_EXISTS.format(tg_id=tg_id), reply_markup=admin_menu_kb())
        return
    await state.update_data(new_admin_tg_id=tg_id)
    await state.set_state(AdminAddAdminStates.confirm)
    preview = format_admin_item(user)
    await message.answer(preview, reply_markup=confirm_kb())


@router.callback_query(AdminAddAdminStates.confirm, ConfirmCB.filter(F.action == "no"))
async def admin_add_confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    """Отказ назначить администратора."""
    await callback.answer()
    await state.clear()
    if callback.message:
        await callback.message.answer(FSM_CANCELLED, reply_markup=admin_menu_kb())


@router.callback_query(AdminAddAdminStates.confirm, ConfirmCB.filter(F.action == "yes"))
async def admin_add_confirm_yes(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Назначает администратора и уведомляет его."""
    await callback.answer()
    if callback.message is None or callback.message.bot is None:
        await state.clear()
        return
    data = await state.get_data()
    tg_id = int(data["new_admin_tg_id"])
    await state.clear()
    user = await UserRepo.add_admin(session, tg_id)
    if user is None:
        await callback.message.answer(
            ADMIN_ADMIN_NOT_FOUND.format(tg_id=tg_id),
            reply_markup=admin_menu_kb(),
        )
        return
    await notify_user(
        callback.message.bot,
        user.tg_id,
        ADMIN_NEW_ADMIN_GRANTED.format(service_name=settings.service_name),
        reply_markup=admin_menu_kb(),
        session=session,
    )
    await callback.message.answer(
        ADMIN_ADMIN_ADDED.format(tg_id=user.tg_id),
        reply_markup=admin_menu_kb(),
    )
    await show_admins(callback.message, session)


@router.callback_query(AdminCB.filter(F.action == "remove"))
async def admin_remove(
    callback: CallbackQuery,
    callback_data: AdminCB,
    session: AsyncSession,
) -> None:
    """Снимает права администратора. Владельца снять нельзя."""
    await callback.answer()
    if callback.message is None:
        return
    if callback_data.user_id == NEW_ITEM_ID:
        return
    target = await session.get(User, callback_data.user_id)
    if target is None:
        await callback.message.answer(ADMIN_ADMIN_NOT_FOUND.format(tg_id=callback_data.user_id))
        return
    if target.tg_id == settings.owner_id:
        await callback.message.answer(ADMIN_ADMIN_CANNOT_REMOVE_OWNER, reply_markup=admin_menu_kb())
        return
    removed = await UserRepo.remove_admin(session, target.tg_id)
    if removed is None:
        await callback.message.answer(ADMIN_ADMIN_CANNOT_REMOVE_OWNER, reply_markup=admin_menu_kb())
        return
    await callback.message.answer(
        ADMIN_ADMIN_REMOVED.format(tg_id=removed.tg_id),
        reply_markup=admin_menu_kb(),
    )
    await show_admins(callback.message, session)
