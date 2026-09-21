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


from sqlalchemy import inspect, text


def _migrate_sqlite(sync_conn) -> None:
    """Добавляет новые колонки в уже существующую SQLite-базу."""
    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())
    if "users" in tables:
        cols = {column["name"] for column in inspector.get_columns("users")}
        if "bonus_balance" not in cols:
            sync_conn.execute(
                text("ALTER TABLE users ADD COLUMN bonus_balance INTEGER DEFAULT 0 NOT NULL")
            )
    if "client_requests" in tables:
        cols = {column["name"] for column in inspector.get_columns("client_requests")}
        statements = {
            "source": "ALTER TABLE client_requests ADD COLUMN source VARCHAR(32) DEFAULT 'quick' NOT NULL",
            "desired_slot": "ALTER TABLE client_requests ADD COLUMN desired_slot VARCHAR(64)",
            "services_text": "ALTER TABLE client_requests ADD COLUMN services_text TEXT",
            "media_file_id": "ALTER TABLE client_requests ADD COLUMN media_file_id VARCHAR(256)",
            "media_type": "ALTER TABLE client_requests ADD COLUMN media_type VARCHAR(32)",
        }
        for name, ddl in statements.items():
            if name not in cols:
                sync_conn.execute(text(ddl))


async def init_db() -> None:
    """Создаёт все таблицы и накатывает лёгкие миграции SQLite."""
    from database import models as _models  # noqa: F401 — регистрация моделей

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_migrate_sqlite)


async def close_db() -> None:
    """Закрывает пул соединений движка."""
    await engine.dispose()
