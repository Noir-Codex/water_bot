# 💧 Smart Telegram Bot for Water Tracking (WaterBot)

*Read this in other languages: [Russian](README_ru.md)*

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/en/latest/)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-lightgrey.svg)](https://docs.python.org/3/library/sqlite3.html)

WaterBot is an asynchronous Telegram bot that helps you maintain proper hydration. Unlike other trackers, it **does not spam** you with notifications every hour. The bot uses a "smart" algorithm: it analyzes your active hours and sends a reminder *only* if you are falling behind your ideal water intake schedule.

---

## ✨ Key Features

- 🎯 **Personalized Goal**: Automatically calculates your daily water intake goal based on your weight using the WHO formula (32 ml per 1 kg).
- 🧠 **Smart Reminders**: Takes your wake-up and sleep times into account. Tracks your current progress and reminds you to drink only when you fall behind schedule, using various text messages for diversity.
- ⚡ **Quick Input**: Convenient inline buttons to add water in one click (150, 250, 350, 500 ml), plus the ability to enter a **custom volume**.
- 📊 **Visual Statistics**: Beautiful text-based progress bars, motivating statuses, and tracking of your daily goal completion.
- ⚙️ **Flexible Settings**: Built-in profile with the ability to change your goal, weight, or sleep hours at any time.

---

## 🛠 Tech Stack

- **Language**: Python 3.13+
- **Framework**: [aiogram 3.x](https://docs.aiogram.dev/) (for asynchronous work with the Telegram API)
- **Database**: SQLite (asynchronous access via `aiosqlite`)
- **Task Scheduler**: [APScheduler](https://apscheduler.readthedocs.io/) (interval progress checks in the background)
- **Environment Management**: `python-dotenv`

---

## 🚀 Installation and Setup

### 1. Preparation
Clone the repository:
```bash
git clone https://github.com/Noir-Codex/water_bot.git
cd water_bot
```

### 2. Setting Up the Virtual Environment
Create and activate a virtual environment to isolate project dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # For macOS/Linux
venv\Scripts\activate   # For Windows
```

### 3. Installing Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuring Environment Variables
Copy the configuration file example:
```bash
cp .env.example .env
```
Then fill `.env` with your data:
```env
# Your token from @BotFather in Telegram:
BOT_TOKEN=token from @BotFather
# SQLite local database file:
DB_PATH=water_bot.db
```

### 5. Running the Bot
While in the virtual environment, start the bot:
```bash
python main.py
```

---

## 💡 How the "Smart" Scheduler Works (`scheduler.py`)

Every **45 minutes**, `APScheduler` triggers a checking algorithm for each user:
1. It requests the current time and compares it against the set "active hours" (from wake-up to sleep).
2. It calculates the *ideal ("expected") water amount* for the current moment via linear interpolation.
3. It additionally checks for the absence of recent reminders (less than 90 minutes ago).
4. If the volume drunk is **less than 80%** of the expected amount for the current minute — the bot sends a reminder.

This approach protects the user from spam if they are drinking their quota on time.
