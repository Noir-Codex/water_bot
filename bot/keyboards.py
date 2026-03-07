"""Инлайн и reply-клавиатуры."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def drink_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора объёма выпитой воды."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💧 Полстакана (150 мл)", callback_data="water:150"),
        ],
        [
            InlineKeyboardButton(text="💧 Стакан (250 мл)", callback_data="water:250"),
        ],
        [
            InlineKeyboardButton(text="💦 Большой стакан (400 мл)", callback_data="water:400"),
        ],
        [
            InlineKeyboardButton(text="🍶 Бутылка (500 мл)", callback_data="water:500"),
        ],
    ])


def main_keyboard() -> ReplyKeyboardMarkup:
    """Главная reply-клавиатура."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💧 Выпил воду"),
                KeyboardButton(text="📊 Мой прогресс"),
            ],
            [
                KeyboardButton(text="📈 Статистика"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ Изменить вес", callback_data="settings:weight")],
        [InlineKeyboardButton(text="🎯 Изменить цель (мл)", callback_data="settings:goal")],
        [InlineKeyboardButton(text="🌅 Время подъёма", callback_data="settings:wake")],
        [InlineKeyboardButton(text="🌙 Время отхода ко сну", callback_data="settings:sleep")],
    ])
