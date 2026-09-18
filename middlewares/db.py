"""Middleware сессии SQLAlchemy для каждого update."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.base import async_session_maker

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Открывает `AsyncSession`, кладёт её в `data["session"]` и закрывает транзакцию."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Выдаёт сессию хендлеру: commit при успехе, rollback при исключении."""
        async with async_session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                logger.exception(
                    "Ошибка при обработке update, транзакция отменена"
                )
                raise
            await session.commit()
            return result
