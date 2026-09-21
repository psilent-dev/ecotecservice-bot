"""Фильтры доступа администратора и владельца."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, User
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.repo import UserRepo


class IsAdmin(BaseFilter):
    """Пропускает владельца, ID из `ADMIN_IDS` и пользователей с флагом администратора."""

    async def __call__(
        self,
        event: TelegramObject,
        session: AsyncSession,
        event_from_user: User | None = None,
    ) -> bool:
        """Проверяет флаг администратора по Telegram ID отправителя."""
        if event_from_user is None:
            return False
        if event_from_user.id == settings.owner_id or event_from_user.id in settings.admin_ids:
            return True
        db_user = await UserRepo.get_by_tg_id(session, event_from_user.id)
        return bool(db_user is not None and db_user.is_admin)


class IsOwner(BaseFilter):
    """Пропускает только владельца сервиса."""

    async def __call__(
        self,
        event: TelegramObject,
        event_from_user: User | None = None,
    ) -> bool:
        """Сравнивает Telegram ID с `settings.owner_id`."""
        if event_from_user is None:
            return False
        return event_from_user.id == settings.owner_id
