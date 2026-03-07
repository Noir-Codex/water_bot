"""Конфигурация бота."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    db_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN не задан в .env файле")
        return cls(
            bot_token=token,
            db_path=os.getenv("DB_PATH", "water_bot.db"),
        )


settings = Settings.from_env()
