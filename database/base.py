"""Асинхронный движок SQLAlchemy и декларативная база моделей."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


def _ensure_sqlite_directory(database_url: str) -> None:
    """Создаёт каталог файла SQLite, если URL указывает на локальный файл."""
    if not database_url.startswith("sqlite"):
        return
    prefix = ":///"
    index = database_url.find(prefix)
    if index == -1:
        return
    raw_path = database_url[index + len(prefix) :]
    if not raw_path or raw_path == ":memory:":
        return
    db_path = Path(raw_path)
    if db_path.parent.as_posix() not in {"", "."}:
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(settings.database_url)

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


async def init_db() -> None:
    """Создаёт все таблицы, зарегистрированные в `Base.metadata`."""
    from database import models as _models  # noqa: F401 — регистрация моделей

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Закрывает пул соединений движка."""
    await engine.dispose()
