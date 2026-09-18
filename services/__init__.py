"""Пакет сервисных функций бота."""

from services.loyalty import (
    apply_discounts_to_request_text,
    consume_discounts,
    get_active_bonuses,
)
from services.notify import notify_admins, notify_user
from services.scheduler import init_scheduler, shutdown_scheduler

__all__ = [
    "apply_discounts_to_request_text",
    "consume_discounts",
    "get_active_bonuses",
    "init_scheduler",
    "notify_admins",
    "notify_user",
    "shutdown_scheduler",
]
