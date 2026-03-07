"""Датаклассы для работы с данными."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    id: int
    telegram_id: int
    weight_kg: float
    daily_goal_ml: int
    wake_hour: int
    sleep_hour: int
    last_reminded_at: Optional[str]


@dataclass
class WaterLog:
    id: int
    user_id: int
    amount_ml: int
    logged_at: str
