"""Вопрос мастеру: текст, фото или аудио."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestSource, RequestType
from database.repo import RequestRepo
from handlers.booking import _username
from handlers.start import ack_event, answer_with_menu, require_client, show_screen
from keyboards.inline import ConfirmCB, MenuCB, admin_request_actions_kb, cancel_kb, question_confirm_kb
from services.notify import notify_admins
from states.client import QuestionStates
from texts import (
    ADMIN_QUESTION_NOTIFY,
    BTN_CANCEL,
    MENU_BUTTONS,
    QUESTION_CONFIRM,
    QUESTION_CREATED,
    QUESTION_EMPTY,
    QUESTION_MEDIA_CAPTION,
    QUESTION_PROMPT,
)
from utils.validators import format_phone_display

router = Router(name="question")


def _extract_media(message: Message) -> tuple[str | None, str | None, str]:
    """file_id, тип вложения и текст/подпись."""
    caption = (message.caption or "").strip()
    text = (message.text or "").strip()
    if message.photo:
        return message.photo[-1].file_id, "photo", caption or QUESTION_MEDIA_CAPTION.format(kind="фото")
    if message.voice:
        return message.voice.file_id, "voice", caption or text or QUESTION_MEDIA_CAPTION.format(kind="аудио")
    if message.audio:
        return message.audio.file_id, "audio", caption or text or QUESTION_MEDIA_CAPTION.format(kind="аудио")
    return None, None, text


@router.callback_query(MenuCB.filter(F.action == "question"))
@router.message(F.text == MENU_BUTTONS["question"])
async def question_entry(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Старт вопроса мастеру."""
    _message, tg_user = await ack_event(event)
    if tg_user is None:
        return
    user = await require_client(event, session, tg_user)
    if user is None:
        return
    await state.clear()
    await state.set_state(QuestionStates.enter_text)
    await show_screen(event, QUESTION_PROMPT, cancel_kb())


@router.callback_query(QuestionStates.enter_text, MenuCB.filter(F.action == "cancel"))
@router.callback_query(QuestionStates.confirm, MenuCB.filter(F.action == "cancel"))
@router.callback_query(QuestionStates.confirm, ConfirmCB.filter(F.action == "no"))
@router.message(QuestionStates.enter_text, F.text == BTN_CANCEL)
@router.message(QuestionStates.confirm, F.text == BTN_CANCEL)
async def question_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Отмена вопроса."""
    _message, tg_user = await ack_event(event)
    if tg_user is None:
        return
    await state.clear()
    user = await require_client(event, session, tg_user)
    if user is None:
        return
    await answer_with_menu(event, user, "↩️ Вопрос не отправлен.")


@router.message(QuestionStates.enter_text, F.photo | F.voice | F.audio | F.text)
async def question_capture(message: Message, state: FSMContext) -> None:
    """Сохраняет вопрос и показывает подтверждение."""
    file_id, media_type, text = _extract_media(message)
    if not text:
        await message.answer(QUESTION_EMPTY, reply_markup=cancel_kb())
        return
    await state.update_data(question=text, media_file_id=file_id, media_type=media_type)
    await state.set_state(QuestionStates.confirm)
    await message.answer(QUESTION_CONFIRM.format(text=text), reply_markup=question_confirm_kb())


@router.callback_query(QuestionStates.confirm, ConfirmCB.filter(F.action == "yes"))
async def question_confirm_yes(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт заявку QUESTION и уведомляет администраторов."""
    await callback.answer()
    if callback.from_user is None:
        return
    user = await require_client(callback, session, callback.from_user)
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    question = str(data.get("question") or "").strip()
    if not question:
        await state.set_state(QuestionStates.enter_text)
        await show_screen(callback, QUESTION_EMPTY, cancel_kb())
        return
    media_file_id = data.get("media_file_id")
    media_type = data.get("media_type")
    request = await RequestRepo.create(
        session,
        user_id=user.id,
        request_type=RequestType.QUESTION,
        text=question,
        source=RequestSource.QUESTION,
        media_file_id=str(media_file_id) if media_file_id else None,
        media_type=str(media_type) if media_type else None,
    )
    if callback.message and callback.message.bot:
        await notify_admins(
            callback.message.bot,
            session,
            ADMIN_QUESTION_NOTIFY.format(
                request_id=request.id,
                name=user.full_name,
                username=_username(user),
                phone=format_phone_display(user.phone) or "не указан",
                text=question,
            ),
            reply_markup=admin_request_actions_kb(
                request.id,
                phone=user.phone,
                source=RequestSource.QUESTION.value,
            ),
        )
    await state.clear()
    await answer_with_menu(callback, user, QUESTION_CREATED)
