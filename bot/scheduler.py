"""
Умный планировщик напоминаний о воде.

Логика:
- Каждые 45 минут проверяет прогресс каждого пользователя
- Рассчитывает "ожидаемое" количество воды на текущее время
- Если отстаёшь от графика и давно не было напоминания — присылает
- Напоминания с разными текстами, без навязчивости
"""
import random
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
from aiogram import Bot

from bot.config import settings
from bot.keyboards import drink_keyboard

# Разнообразные тексты напоминаний (не один и тот же каждый раз)
REMINDER_TEXTS = [
    "Привет! Кажется, ты немного отстаёшь от водного графика 💧\nСделай пару глотков прямо сейчас?",
    "Небольшое напоминание: твоё тело ждёт воды! 🚰\nДолго не пил — самое время исправить.",
    "Вода — это жизнь, а ты, похоже, сегодня немного забыл об этом 💦\nДавай наверстаем?",
    "Организм сигналит: воды маловато! 🙂\nНалей стаканчик — и отметь здесь.",
    "Ты занят делами, но вода важнее большинства задач 😄💧\nОдин глоток сейчас — и продолжай!",
    "Тихое напоминание от твоего бота: пора пить воду 🌊\nОтстаёшь от дневной нормы — нагоним!",
    "Как дела с водичкой? 😏 Судя по данным — не очень.\nИсправим это прямо сейчас?",
    "По статистике ты сейчас должен был выпить больше 💧\nНе откладывай — занять полминуты!",
]

# Минимальный интервал между напоминаниями (в минутах)
MIN_REMIND_INTERVAL = 90


def _progress_bar(current: int, goal: int, length: int = 10) -> str:
    """Текстовый прогресс-бар."""
    filled = int(length * min(current, goal) / goal)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(100 * min(current, goal) / goal)
    return f"[{bar}] {percent}%"


async def get_today_intake(db: aiosqlite.Connection, user_id: int) -> int:
    """Считает сколько мл выпито сегодня (по локальному времени)."""
    async with db.execute(
        """
        SELECT COALESCE(SUM(amount_ml), 0) as total
        FROM water_log
        WHERE user_id = ?
          AND date(logged_at) = date('now', 'localtime')
        """,
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0


async def _get_expected_intake(
    daily_goal: int, wake_hour: int, sleep_hour: int, now: datetime
) -> int:
    """
    Рассчитывает ожидаемое количество воды к текущему моменту
    (линейная интерполяция в пределах активных часов).
    """
    current_hour = now.hour + now.minute / 60.0
    if current_hour <= wake_hour:
        return 0
    if current_hour >= sleep_hour:
        return daily_goal
    active_hours = sleep_hour - wake_hour
    elapsed = current_hour - wake_hour
    return int(daily_goal * elapsed / active_hours)


async def check_and_remind(bot: Bot) -> None:
    """
    Основная задача планировщика.
    Проверяет каждого пользователя и при необходимости отправляет напоминание.
    """
    now = datetime.now()

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT * FROM users") as cursor:
            users = await cursor.fetchall()

        for user in users:
            telegram_id = user["telegram_id"]
            daily_goal = user["daily_goal_ml"]
            wake_hour = user["wake_hour"]
            sleep_hour = user["sleep_hour"]
            last_reminded_at: Optional[str] = user["last_reminded_at"]

            # Не беспокоить вне активных часов
            current_hour = now.hour
            if current_hour < wake_hour or current_hour >= sleep_hour:
                continue

            # Проверяем: прошло ли достаточно времени с последнего напоминания
            if last_reminded_at:
                last_dt = datetime.fromisoformat(last_reminded_at)
                if (now - last_dt).total_seconds() < MIN_REMIND_INTERVAL * 60:
                    continue

            # Считаем текущий прогресс
            intake = await get_today_intake(db, user["id"])

            # Если выпито >= 100% нормы — не беспокоить
            if intake >= daily_goal:
                continue

            # Считаем ожидаемое количество
            expected = await _get_expected_intake(daily_goal, wake_hour, sleep_hour, now)

            # Если прогресс >= 80% от ожидаемого — всё хорошо, не беспокоить
            if expected == 0 or intake >= 0.80 * expected:
                continue

            # Пора напомнить!
            text = random.choice(REMINDER_TEXTS)
            bar = _progress_bar(intake, daily_goal)
            remaining = max(0, daily_goal - intake)

            full_text = (
                f"{text}\n\n"
                f"📊 Прогресс за день: {bar}\n"
                f"💧 Выпито: {intake} мл / {daily_goal} мл\n"
                f"⏳ Осталось: {remaining} мл"
            )

            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=full_text,
                    reply_markup=drink_keyboard(),
                )
                # Обновляем время последнего напоминания
                await db.execute(
                    "UPDATE users SET last_reminded_at = ? WHERE telegram_id = ?",
                    (now.isoformat(), telegram_id),
                )
                await db.commit()
            except Exception:
                # Пользователь мог заблокировать бота — просто пропускаем
                pass


async def get_user_stats_text(db: aiosqlite.Connection, user_id: int, daily_goal: int) -> str:
    """Возвращает статистику за день в виде текста."""
    intake = await get_today_intake(db, user_id)
    bar = _progress_bar(intake, daily_goal)
    remaining = max(0, daily_goal - intake)
    percent = int(100 * min(intake, daily_goal) / daily_goal)

    if percent >= 100:
        status = "🎉 Отлично! Дневная норма выполнена!"
    elif percent >= 75:
        status = "👍 Хороший прогресс, почти у цели!"
    elif percent >= 50:
        status = "😊 Половина пути пройдена!"
    elif percent >= 25:
        status = "💪 Начало положено, продолжай!"
    else:
        status = "⚠️ Нужно больше воды сегодня!"

    return (
        f"📊 <b>Водный баланс на сегодня</b>\n\n"
        f"{bar}\n\n"
        f"💧 Выпито: <b>{intake} мл</b>\n"
        f"🎯 Цель: <b>{daily_goal} мл</b>\n"
        f"⏳ Осталось: <b>{remaining} мл</b>\n\n"
        f"{status}"
    )
