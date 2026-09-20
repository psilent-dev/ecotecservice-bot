"""FSM вопроса мастеру."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RequestType
from database.repo import RequestRepo
from handlers.booking import cancel_client_fsm, notify_admins_new_request
from handlers.start import answer_with_menu, require_client
from keyboards.reply import cancel_kb, confirm_kb
from states.client import QuestionStates
from texts import (
    BTN_CANCEL,
    BTN_CONFIRM,
    MENU_BUTTONS,
    QUESTION_CANCELLED,
    QUESTION_CONFIRM,
    QUESTION_CREATED,
    QUESTION_EMPTY,
    QUESTION_PROMPT,
)

router = Router(name="question")


@router.message(F.text == MENU_BUTTONS["question"])
async def question_entry(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Старт вопроса мастеру."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        return
    await state.clear()
    await state.set_state(QuestionStates.enter_text)
    await message.answer(QUESTION_PROMPT, reply_markup=cancel_kb())


@router.message(QuestionStates.enter_text, F.text == BTN_CANCEL)
@router.message(QuestionStates.confirm, F.text == BTN_CANCEL)
async def question_cancel_button(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Выход из сценария вопроса."""
    await cancel_client_fsm(message, state, session, QUESTION_CANCELLED)


@router.message(QuestionStates.enter_text, F.text)
async def question_enter_text(message: Message, state: FSMContext) -> None:
    """Сохраняет текст вопроса и показывает подтверждение."""
    text = (message.text or "").strip()
    if not text:
        await message.answer(QUESTION_EMPTY, reply_markup=cancel_kb())
        return
    await state.update_data(question=text)
    await state.set_state(QuestionStates.confirm)
    await message.answer(QUESTION_CONFIRM.format(text=text), reply_markup=confirm_kb())


@router.message(QuestionStates.confirm, F.text == BTN_CONFIRM)
async def question_confirm_yes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создаёт заявку QUESTION и уведомляет администраторов."""
    if message.from_user is None:
        return
    user = await require_client(message, session, message.from_user)
    if user is None:
        await state.clear()
        return
    data = await state.get_data()
    question = str(data.get("question", "")).strip()
    if not question:
        await state.set_state(QuestionStates.enter_text)
        await message.answer(QUESTION_EMPTY, reply_markup=cancel_kb())
        return
    request = await RequestRepo.create(
        session,
        user_id=user.id,
        request_type=RequestType.QUESTION,
        text=question,
    )
    await notify_admins_new_request(
        message,
        session,
        request_id=request.id,
        request_type=RequestType.QUESTION,
        user=user,
        service=None,
        car_info=None,
        text=question,
    )
    await state.clear()
    await answer_with_menu(
        message,
        user,
        QUESTION_CREATED.format(request_id=request.id),
    )


@router.message(QuestionStates.confirm, F.text)
async def question_confirm_hint(message: Message) -> None:
    """Напоминает подтвердить кнопками."""
    await message.answer(QUESTION_CONFIRM.format(text="—"), reply_markup=confirm_kb())
