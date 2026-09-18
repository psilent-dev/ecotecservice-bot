"""Конфигурация бота «Экотек Сервис» из переменных окружения."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, читаемые из `.env` и окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str
    owner_id: int
    # NoDecode: иначе pydantic-settings пытается разобрать «123,456» как JSON.
    admin_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    database_url: str
    tz: str = "Europe/Moscow"
    service_name: str
    service_phone: str
    service_address: str
    service_hours: str
    service_maps_url: str
    bot_username: str
    # Если api.telegram.org недоступен, например: socks5://127.0.0.1:1080
    telegram_proxy: str | None = None

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int] | int | None) -> list[int]:
        """Преобразует `ADMIN_IDS` из строки «123,456» в список целых."""
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, int):
            return [value]
        if isinstance(value, str):
            parts = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
            return [int(chunk) for chunk in parts]
        raise ValueError("Некорректный формат ADMIN_IDS: ожидается строка «123,456»")

    @field_validator("telegram_proxy", mode="before")
    @classmethod
    def empty_proxy_to_none(cls, value: str | None) -> str | None:
        """Пустая строка в `.env` означает «прокси нет»."""
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @model_validator(mode="after")
    def ensure_owner_in_admins(self) -> "Settings":
        """Гарантирует, что владелец всегда входит в список администраторов."""
        if self.owner_id not in self.admin_ids:
            self.admin_ids = [*self.admin_ids, self.owner_id]
        return self


settings = Settings()
