"""Клиентские роутеры бота «Экотек Сервис»."""

from aiogram import Router

from handlers.booking import router as booking_router
from handlers.contacts import router as contacts_router
from handlers.fallback import router as fallback_router
from handlers.miniapp_ticket import router as miniapp_ticket_router
from handlers.profile import router as profile_router
from handlers.question import router as question_router
from handlers.start import router as start_router

__all__ = [
    "booking_router",
    "contacts_router",
    "fallback_router",
    "miniapp_ticket_router",
    "profile_router",
    "question_router",
    "setup_routers",
    "start_router",
]


def setup_routers() -> Router:
    """Собирает клиентские роутеры."""
    root = Router(name="client")
    root.include_router(start_router)
    root.include_router(booking_router)
    root.include_router(miniapp_ticket_router)
    root.include_router(question_router)
    root.include_router(profile_router)
    root.include_router(contacts_router)
    root.include_router(fallback_router)
    return root
