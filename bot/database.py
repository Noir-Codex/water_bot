"""Работа с базой данных SQLite через aiosqlite."""
import aiosqlite

from bot.config import settings

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    weight_kg REAL DEFAULT 70,
    daily_goal_ml INTEGER DEFAULT 2100,
    wake_hour INTEGER DEFAULT 7,
    sleep_hour INTEGER DEFAULT 23,
    last_reminded_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

CREATE_WATER_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS water_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount_ml INTEGER NOT NULL,
    logged_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
"""


async def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_WATER_LOG_TABLE)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Возвращает соединение с БД (используется в middleware)."""
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    return db
