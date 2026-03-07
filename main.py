"""
Точка входа WaterBot.
Инициализирует бота, регистрирует роутеры, запускает планировщик и polling.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings
from bot.database import init_db
from bot.middlewares import DatabaseMiddleware
from bot.handlers import start, water, stats
from bot.scheduler import check_and_remind

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # Инициализируем БД
    await init_db()
    logger.info("База данных инициализирована")

    # Создаём бота и диспетчер
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем middleware для базы данных
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(water.router)
    dp.include_router(stats.router)

    # Запускаем планировщик умных напоминаний
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        check_and_remind,
        trigger="interval",
        minutes=45,
        kwargs={"bot": bot},
        id="water_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Планировщик напоминаний запущен (каждые 45 мин)")

    # Запускаем polling
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
