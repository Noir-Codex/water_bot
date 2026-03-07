"""
Обработчик статистики — /stats и кнопка «📈 Статистика».
Показывает детальную статистику за сегодня и неделю.
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite

router = Router()


async def _get_user(db: aiosqlite.Connection, telegram_id: int):
    async with db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ) as cursor:
        return await cursor.fetchone()


def _bar(current: int, goal: int, length: int = 10) -> str:
    filled = int(length * min(current, goal) / goal)
    return "█" * filled + "░" * (length - filled)


@router.message(F.text == "📈 Статистика")
@router.message(Command("stats"))
async def stats_handler(message: Message, db: aiosqlite.Connection) -> None:
    user = await _get_user(db, message.from_user.id)
    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    user_id = user["id"]
    daily_goal = user["daily_goal_ml"]

    # Статистика за сегодня
    async with db.execute(
        """
        SELECT COALESCE(SUM(amount_ml), 0) as total, COUNT(*) as cnt
        FROM water_log
        WHERE user_id = ? AND date(logged_at) = date('now', 'localtime')
        """,
        (user_id,),
    ) as cursor:
        today = await cursor.fetchone()

    today_total = int(today["total"])
    today_count = int(today["cnt"])

    # Статистика за 7 дней
    async with db.execute(
        """
        SELECT
            date(logged_at) as day,
            SUM(amount_ml) as total
        FROM water_log
        WHERE user_id = ?
          AND date(logged_at) >= date('now', '-6 days', 'localtime')
        GROUP BY day
        ORDER BY day DESC
        """,
        (user_id,),
    ) as cursor:
        week_rows = await cursor.fetchall()

    # Средний показатель за неделю
    if week_rows:
        avg_week = int(sum(r["total"] for r in week_rows) / len(week_rows))
        best_day_row = max(week_rows, key=lambda r: r["total"])
        best_day_total = int(best_day_row["total"])
        best_day_date = best_day_row["day"]
    else:
        avg_week = 0
        best_day_total = 0
        best_day_date = "—"

    today_bar = _bar(today_total, daily_goal)
    week_bar = _bar(avg_week, daily_goal)
    percent_today = int(100 * min(today_total, daily_goal) / daily_goal)

    # Формируем историю по дням
    history_lines = []
    for row in week_rows[:7]:
        d = row["day"]
        t = int(row["total"])
        b = _bar(t, daily_goal, length=6)
        emoji = "✅" if t >= daily_goal else ("🟡" if t >= daily_goal * 0.5 else "🔴")
        history_lines.append(f"  {emoji} {d}: {b} {t} мл")

    history_text = "\n".join(history_lines) if history_lines else "  Данных пока нет"

    text = (
        f"📈 <b>Статистика водного баланса</b>\n\n"
        f"<b>Сегодня</b>\n"
        f"[{today_bar}] {percent_today}%\n"
        f"💧 {today_total} мл / {daily_goal} мл\n"
        f"🥤 Записей: {today_count}\n\n"
        f"<b>Средний за 7 дней</b>\n"
        f"[{week_bar}] {avg_week} мл/день\n\n"
        f"<b>Лучший день:</b> {best_day_date} — {best_day_total} мл\n\n"
        f"<b>История (последние {len(week_rows)} дн.):</b>\n"
        f"{history_text}"
    )

    await message.answer(text, parse_mode="HTML")
