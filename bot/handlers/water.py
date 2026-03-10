"""
Обработчики логирования воды.
Кнопка «💧 Выпил воду» и callback-и с выбором объёма.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
import aiosqlite

from bot.keyboards import drink_keyboard
from bot.scheduler import get_today_intake, get_user_stats_text

router = Router()


async def _get_user(db: aiosqlite.Connection, telegram_id: int):
    async with db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ) as cursor:
        return await cursor.fetchone()


# ─── Нажатие reply-кнопки «💧 Выпил воду» ───────────────────────────────────

@router.message(F.text == "💧 Выпил воду")
async def water_button(message: Message, db: aiosqlite.Connection) -> None:
    user = await _get_user(db, message.from_user.id)
    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    await message.answer(
        "💧 Сколько выпил?\nВыбери объём:",
        reply_markup=drink_keyboard(),
    )


# ─── Callback выбора объёма воды ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("water:") & ~F.data.endswith("custom"))
async def water_logged(callback: CallbackQuery, db: aiosqlite.Connection) -> None:
    user = await _get_user(db, callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди настройку: /start")
        return

    amount_ml = int(callback.data.split(":")[1])

    # Записываем в БД
    await db.execute(
        "INSERT INTO water_log (user_id, amount_ml) VALUES (?, ?)",
        (user["id"], amount_ml),
    )
    # Сбрасываем таймер напоминаний (раз пьёт — напоминать не нужно скоро)
    from datetime import datetime
    await db.execute(
        "UPDATE users SET last_reminded_at = ? WHERE id = ?",
        (datetime.now().isoformat(), user["id"]),
    )
    await db.commit()

    today_intake = await get_today_intake(db, user["id"])
    daily_goal = user["daily_goal_ml"]
    remaining = max(0, daily_goal - today_intake)

    if today_intake >= daily_goal:
        result_text = (
            f"🎉 <b>+{amount_ml} мл добавлено!</b>\n\n"
            f"✅ Дневная норма выполнена! ({today_intake} / {daily_goal} мл)\n"
            f"Отличная работа, так держать! 💪"
        )
    else:
        result_text = (
            f"💧 <b>+{amount_ml} мл добавлено!</b>\n\n"
            f"📊 Сегодня: {today_intake} / {daily_goal} мл\n"
            f"⏳ Осталось: {remaining} мл"
        )

    await callback.message.edit_text(result_text, parse_mode="HTML")
    await callback.answer(f"✅ +{amount_ml} мл записано!")


# ─── Свой объём ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "water:custom")
async def water_custom_ask(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "✏️ Введи объём воды в мл (например: <b>320</b>):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(F.text.regexp(r"^\d+$"))
async def water_custom_input(message: Message, db: aiosqlite.Connection) -> None:
    user = await _get_user(db, message.from_user.id)
    if not user:
        return

    amount_ml = int(message.text)
    if not (10 <= amount_ml <= 5000):
        await message.answer("Введи число от 10 до 5000 мл.")
        return

    from datetime import datetime
    await db.execute(
        "INSERT INTO water_log (user_id, amount_ml) VALUES (?, ?)",
        (user["id"], amount_ml),
    )
    await db.execute(
        "UPDATE users SET last_reminded_at = ? WHERE id = ?",
        (datetime.now().isoformat(), user["id"]),
    )
    await db.commit()

    today_intake = await get_today_intake(db, user["id"])
    daily_goal = user["daily_goal_ml"]
    remaining = max(0, daily_goal - today_intake)

    if today_intake >= daily_goal:
        result_text = (
            f"🎉 <b>+{amount_ml} мл добавлено!</b>\n\n"
            f"✅ Дневная норма выполнена! ({today_intake} / {daily_goal} мл)\n"
            f"Отличная работа! 💪"
        )
    else:
        result_text = (
            f"💧 <b>+{amount_ml} мл добавлено!</b>\n\n"
            f"📊 Сегодня: {today_intake} / {daily_goal} мл\n"
            f"⏳ Осталось: {remaining} мл"
        )

    await message.answer(result_text, parse_mode="HTML", reply_markup=drink_keyboard())


# ─── /status — быстрый прогресс ──────────────────────────────────────────────

@router.message(F.text == "📊 Мой прогресс")
async def status_button(message: Message, db: aiosqlite.Connection) -> None:
    user = await _get_user(db, message.from_user.id)
    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    text = await get_user_stats_text(db, user["id"], user["daily_goal_ml"])
    await message.answer(text, reply_markup=drink_keyboard(), parse_mode="HTML")
