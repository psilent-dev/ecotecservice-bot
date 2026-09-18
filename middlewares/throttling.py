"""Антифлуд: не чаще одного апдейта за 0.5 секунды на пользователя."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT = 0.5
_CLEANUP_INTERVAL = 30.0
_STALE_AFTER = 15.0


class ThrottlingMiddleware(BaseMiddleware):
    """Игнорирует слишком частые апдейты одного `user_id`, без ответа пользователю."""

    def __init__(self, rate_limit: float = DEFAULT_RATE_LIMIT) -> None:
        """Сохраняет интервал и словарь последних апдейтов в памяти процесса."""
        super().__init__()
        self.rate_limit = rate_limit
        self._last_update: dict[int, float] = {}
        self._last_cleanup = time.monotonic()

    def _cleanup(self, now: float) -> None:
        """Удаляет устаревшие метки, чтобы словарь не рос безгранично."""
        if now - self._last_cleanup < _CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        cutoff = now - max(self.rate_limit * 4, _STALE_AFTER)
        stale_ids = [user_id for user_id, ts in self._last_update.items() if ts < cutoff]
        for user_id in stale_ids:
            del self._last_update[user_id]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Пропускает апдейт либо молча отбрасывает его при превышении лимита."""
        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        now = time.monotonic()
        self._cleanup(now)
        last = self._last_update.get(user.id)
        if last is not None and now - last < self.rate_limit:
            logger.debug("Throttled user_id=%s", user.id)
            return None

        self._last_update[user.id] = now
        return await handler(event, data)
