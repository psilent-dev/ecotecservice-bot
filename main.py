"""Точка входа бота «Экотек Сервис»."""

from __future__ import annotations

import asyncio
import logging
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from config import settings
from database.base import close_db, init_db
from handlers.admin_admins import router as admin_admins_router
from handlers.admin_broadcast import router as admin_broadcast_router
from handlers.admin_entry import router as admin_entry_router
from handlers.admin_extra import (
    AcceptingRequestsMiddleware,
    BlockedUserMiddleware,
    router as admin_extra_router,
)
from handlers.admin_promo import router as admin_promo_router
from handlers.admin_requests import router as admin_requests_router
from handlers.admin_services import router as admin_services_router
from handlers.booking import router as booking_router
from handlers.contacts import router as contacts_router
from handlers.fallback import router as fallback_router
from handlers.price_request import router as price_request_router
from handlers.profile import router as profile_router
from handlers.question import router as question_router
from handlers.start import router as start_router
from middlewares.db import DbSessionMiddleware
from middlewares.throttling import ThrottlingMiddleware
from services.scheduler import init_scheduler, shutdown_scheduler
from texts import ERROR_GLOBAL

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """INFO в консоль и во вращающийся файл logs/bot.log."""
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        logs_dir / "bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)


def setup_dispatcher() -> Dispatcher:
    """Собирает диспетчер, миддлвари и роутеры в нужном порядке."""
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(ThrottlingMiddleware())
    dispatcher.update.middleware(DbSessionMiddleware())
    dispatcher.update.middleware(BlockedUserMiddleware())
    dispatcher.update.middleware(AcceptingRequestsMiddleware())

    dispatcher.include_router(admin_entry_router)
    dispatcher.include_router(start_router)
    dispatcher.include_router(admin_requests_router)
    dispatcher.include_router(admin_broadcast_router)
    dispatcher.include_router(admin_services_router)
    dispatcher.include_router(admin_promo_router)
    dispatcher.include_router(admin_admins_router)
    dispatcher.include_router(admin_extra_router)
    dispatcher.include_router(booking_router)
    dispatcher.include_router(price_request_router)
    dispatcher.include_router(question_router)
    dispatcher.include_router(profile_router)
    dispatcher.include_router(contacts_router)
    dispatcher.include_router(fallback_router)
    return dispatcher


async def on_shutdown() -> None:
    """Останавливает планировщик и закрывает БД."""
    await shutdown_scheduler()
    await close_db()
    logger.info("Остановка завершена")


def build_bot() -> Bot:
    """Создаёт бота; при заданном `TELEGRAM_PROXY` ходит в API через прокси."""
    session: AiohttpSession | None = None
    if settings.telegram_proxy:
        session = AiohttpSession(proxy=settings.telegram_proxy)
        logger.info("Подключение к Telegram через прокси")
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def main() -> None:
    """Инициализация и long polling."""
    setup_logging()
    bot = build_bot()
    dispatcher = setup_dispatcher()

    @dispatcher.error()
    async def on_error(event: ErrorEvent) -> bool:
        """Логирует traceback и уведомляет владельца в личные сообщения."""
        tb = "".join(
            traceback.format_exception(type(event.exception), event.exception, event.exception.__traceback__)
        )
        logger.error("Необработанная ошибка:\n%s", tb)
        try:
            await bot.send_message(settings.owner_id, ERROR_GLOBAL)
        except TelegramAPIError:
            logger.exception("Не удалось уведомить владельца об ошибке")
        return True

    dispatcher.shutdown.register(on_shutdown)

    await init_db()
    init_scheduler(bot)
    logger.info("Бот запущен")
    while True:
        try:
            await dispatcher.start_polling(bot)
            break
        except TelegramNetworkError:
            logger.error(
                "Нет связи с api.telegram.org. "
                "Проверьте интернет или задайте TELEGRAM_PROXY в .env. "
                "Повтор через 15 секунд…"
            )
            await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
