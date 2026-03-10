"""
Обработчики /start, /settings и онбординг через FSM.
Собирает вес, время подъёма и отхода ко сну, рассчитывает дневную норму воды.
"""
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
import aiosqlite

from bot.keyboards import main_keyboard, settings_keyboard

router = Router()


class Onboarding(StatesGroup):
    weight = State()
    wake_hour = State()
    sleep_hour = State()
    confirm_goal = State()


class ChangeSettings(StatesGroup):
    weight = State()
    goal = State()
    wake = State()
    sleep = State()


def _calculate_goal(weight_kg: float) -> int:
    """Рассчитывает дневную норму воды по весу (32 мл/кг)."""
    return int(weight_kg * 32)


async def _get_or_create_user(db: aiosqlite.Connection, telegram_id: int) -> dict | None:
    async with db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ) as cursor:
        return await cursor.fetchone()


@router.message(CommandStart())
async def cmd_start(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    user = await _get_or_create_user(db, message.from_user.id)

    if user:
        await message.answer(
            f"👋 С возвращением! Ты уже настроен.\n\n"
            f"🎯 Твоя дневная норма: <b>{user['daily_goal_ml']} мл</b>\n\n"
            f"Нажми <b>📊 Мой прогресс</b>, чтобы посмотреть статус на сегодня.",
            reply_markup=main_keyboard(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "👋 Привет! Я <b>WaterBot</b> — помогу поддерживать водный баланс.\n\n"
        "Я буду умно напоминать тебе пить воду — без навязчивости, "
        "только когда действительно нужно 💧\n\n"
        "Сначала пара вопросов. <b>Какой у тебя вес (в кг)?</b>\n"
        "Это нужно для расчёта дневной нормы воды.",
        parse_mode="HTML",
    )
    await state.set_state(Onboarding.weight)


@router.message(Onboarding.weight)
async def onboarding_weight(message: Message, state: FSMContext) -> None:
    try:
        weight = float(message.text.replace(",", "."))
        if not (30 <= weight <= 300):
            raise ValueError
    except ValueError:
        await message.answer("Введи вес числом, например: <b>70</b>", parse_mode="HTML")
        return

    goal = _calculate_goal(weight)
    await state.update_data(weight=weight, goal=goal)
    await message.answer(
        f"⚖️ Вес: <b>{weight} кг</b>\n"
        f"💧 Рассчитанная норма: <b>{goal} мл/день</b>\n\n"
        f"Во сколько ты обычно просыпаешься?\n"
        f"Напиши только час, например: <b>7</b>",
        parse_mode="HTML",
    )
    await state.set_state(Onboarding.wake_hour)


@router.message(Onboarding.wake_hour)
async def onboarding_wake(message: Message, state: FSMContext) -> None:
    try:
        hour = int(message.text.strip())
        if not (0 <= hour <= 23):
            raise ValueError
    except ValueError:
        await message.answer("Введи час числом от 0 до 23, например: <b>7</b>", parse_mode="HTML")
        return

    await state.update_data(wake_hour=hour)
    await message.answer(
        f"🌅 Подъём: <b>{hour}:00</b>\n\n"
        f"А во сколько ложишься спать? Напиши час, например: <b>23</b>",
        parse_mode="HTML",
    )
    await state.set_state(Onboarding.sleep_hour)


@router.message(Onboarding.sleep_hour)
async def onboarding_sleep(
    message: Message,
    state: FSMContext,
    db: aiosqlite.Connection,
) -> None:
    try:
        hour = int(message.text.strip())
        if not (0 <= hour <= 23):
            raise ValueError
    except ValueError:
        await message.answer("Введи час числом от 0 до 23, например: <b>23</b>", parse_mode="HTML")
        return

    data = await state.get_data()
    wake = data["wake_hour"]

    # Часы 0-5 считаем «следующим днём» (полночь / поздняя ночь) — всегда OK
    if hour > 5 and hour <= wake:
        await message.answer(
            f"Время сна должно быть позже времени подъёма ({wake}:00).\n"
            f"Или введи 0–5, если ложишься уже после полуночи.",
            parse_mode="HTML",
        )
        return

    await state.update_data(sleep_hour=hour)
    data = await state.get_data()

    # Сохраняем пользователя в БД
    await db.execute(
        """
        INSERT INTO users (telegram_id, weight_kg, daily_goal_ml, wake_hour, sleep_hour)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            weight_kg = excluded.weight_kg,
            daily_goal_ml = excluded.daily_goal_ml,
            wake_hour = excluded.wake_hour,
            sleep_hour = excluded.sleep_hour
        """,
        (
            message.from_user.id,
            data["weight"],
            data["goal"],
            data["wake_hour"],
            hour,
        ),
    )
    await db.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Настройка завершена!</b>\n\n"
        f"⚖️ Вес: {data['weight']} кг\n"
        f"💧 Дневная норма: <b>{data['goal']} мл</b>\n"
        f"🌅 Активные часы: {data['wake_hour']}:00 — {hour}:00\n\n"
        f"Теперь я буду умно напоминать тебе о воде только тогда, "
        f"когда ты действительно отстаёшь от нормы 🎯\n\n"
        f"Нажми <b>💧 Выпил воду</b>, чтобы отметить стакан воды!",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )


# ──────────────────────────── Настройки ──────────────────────────────────────

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message, db: aiosqlite.Connection) -> None:
    user = await _get_or_create_user(db, message.from_user.id)
    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    await message.answer(
        f"⚙️ <b>Твои настройки</b>\n\n"
        f"⚖️ Вес: {user['weight_kg']} кг\n"
        f"🎯 Дневная норма: {user['daily_goal_ml']} мл\n"
        f"🌅 Подъём: {user['wake_hour']}:00\n"
        f"🌙 Сон: {user['sleep_hour']}:00\n\n"
        f"Что хочешь изменить?",
        reply_markup=settings_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings:weight")
async def settings_change_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("⚖️ Введи новый вес в кг, например: <b>72</b>", parse_mode="HTML")
    await state.set_state(ChangeSettings.weight)
    await callback.answer()


@router.message(ChangeSettings.weight)
async def apply_weight(message: Message, state: FSMContext, db: aiosqlite.Connection) -> None:
    try:
        weight = float(message.text.replace(",", "."))
        if not (30 <= weight <= 300):
            raise ValueError
    except ValueError:
        await message.answer("Введи вес числом, например: <b>70</b>", parse_mode="HTML")
        return

    goal = _calculate_goal(weight)
    await db.execute(
        "UPDATE users SET weight_kg = ?, daily_goal_ml = ? WHERE telegram_id = ?",
        (weight, goal, message.from_user.id),
    )
    await db.commit()
    await state.clear()
    await message.answer(
        f"✅ Вес обновлён: <b>{weight} кг</b>\nНовая норма воды: <b>{goal} мл/день</b>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings:goal")
async def settings_change_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "🎯 Введи дневную норму воды в мл, например: <b>2500</b>", parse_mode="HTML"
    )
    await state.set_state(ChangeSettings.goal)
    await callback.answer()


@router.message(ChangeSettings.goal)
async def apply_goal(message: Message, state: FSMContext, db: aiosqlite.Connection) -> None:
    try:
        goal = int(message.text.strip())
        if not (500 <= goal <= 8000):
            raise ValueError
    except ValueError:
        await message.answer(
            "Введи норму в мл числом от 500 до 8000, например: <b>2500</b>", parse_mode="HTML"
        )
        return

    await db.execute(
        "UPDATE users SET daily_goal_ml = ? WHERE telegram_id = ?",
        (goal, message.from_user.id),
    )
    await db.commit()
    await state.clear()
    await message.answer(
        f"✅ Норма воды обновлена: <b>{goal} мл/день</b>", parse_mode="HTML"
    )


@router.callback_query(F.data == "settings:wake")
async def settings_change_wake(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "🌅 Введи час подъёма (0–23), например: <b>7</b>", parse_mode="HTML"
    )
    await state.set_state(ChangeSettings.wake)
    await callback.answer()


@router.message(ChangeSettings.wake)
async def apply_wake(message: Message, state: FSMContext, db: aiosqlite.Connection) -> None:
    try:
        hour = int(message.text.strip())
        if not (0 <= hour <= 23):
            raise ValueError
    except ValueError:
        await message.answer("Введи час числом от 0 до 23", parse_mode="HTML")
        return

    await db.execute(
        "UPDATE users SET wake_hour = ? WHERE telegram_id = ?",
        (hour, message.from_user.id),
    )
    await db.commit()
    await state.clear()
    await message.answer(f"✅ Время подъёма: <b>{hour}:00</b>", parse_mode="HTML")


@router.callback_query(F.data == "settings:sleep")
async def settings_change_sleep(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "🌙 Введи час отхода ко сну (0–23), например: <b>23</b>", parse_mode="HTML"
    )
    await state.set_state(ChangeSettings.sleep)
    await callback.answer()


@router.message(ChangeSettings.sleep)
async def apply_sleep(message: Message, state: FSMContext, db: aiosqlite.Connection) -> None:
    try:
        hour = int(message.text.strip())
        if not (0 <= hour <= 23):
            raise ValueError
    except ValueError:
        await message.answer("Введи час числом от 0 до 23", parse_mode="HTML")
        return

    # Получаем текущий wake_hour чтобы валидировать
    async with db.execute(
        "SELECT wake_hour FROM users WHERE telegram_id = ?", (message.from_user.id,)
    ) as cursor:
        row = await cursor.fetchone()
    wake = row["wake_hour"] if row else 7

    if hour > 5 and hour <= wake:
        await message.answer(
            f"Время сна должно быть позже подъёма ({wake}:00).\n"
            f"Или введи 0–5, если ложишься после полуночи.",
            parse_mode="HTML",
        )
        return

    await db.execute(
        "UPDATE users SET sleep_hour = ? WHERE telegram_id = ?",
        (hour, message.from_user.id),
    )
    await db.commit()
    await state.clear()
    await message.answer(f"✅ Время сна: <b>{hour}:00</b>", parse_mode="HTML")
