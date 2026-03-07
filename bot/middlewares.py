"""Middleware для передачи соединения с БД в хендлеры."""
from typing import Any, Awaitable, Callable, Dict

import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.config import settings


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            data["db"] = db
            return await handler(event, data)
