import os
import sqlite3
import httpx
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# 🔑 ВСТАВЬ СЮДА СВОИ КЛЮЧИ
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# ============================================================
# 🐱 КАРТИНКА
# ============================================================
# Положи файл kot.jpg рядом с bot.py
START_IMAGE = "kot.jpg"

# ============================================================
# 🤖 НАСТРОЙКИ ИИ
# ============================================================

MODEL = "openai/gpt-oss-20b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """
Ты — Вась AI, дружелюбный Telegram-ассистент.
Отвечай понятно, живо и по делу.
Общайся на русском языке, если пользователь пишет по-русски.
Не представляйся человеком.
"""

# ============================================================
# 🧠 ПАМЯТЬ
# ============================================================

DB_FILE = "vash_memory.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )

    # Оставляем последние 40 сообщений
    cur.execute("""
        DELETE FROM messages
        WHERE user_id = ?
        AND id NOT IN (
            SELECT id
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 40
        )
    """, (user_id, user_id))

    conn.commit()
    conn.close()


def get_history(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT role, content
        FROM messages
        WHERE user_id = ?
        ORDER BY id ASC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    history = []

    for role, content in rows:
        history.append({
            "role": role,
            "content": content
        })

    return history


def clear_history(user_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM messages WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


# ============================================================
# 🤖 ЗАПРОС К GROQ
# ============================================================

async def ask_ai(user_id, text):

    history = get_history(user_id)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": text
    })

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:

            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=data
            )

            if response.status_code != 200:
                print("Groq error:", response.text)
                return "⚠️ Не удалось получить ответ от ИИ."

            result = response.json()

            answer = result["choices"][0]["message"]["content"]

            save_message(user_id, "user", text)
            save_message(user_id, "assistant", answer)

            return answer

    except Exception as e:
        print("ERROR:", e)
        return "⚠️ Произошла ошибка при обращении к ИИ."


# ============================================================
# 🏠 ГЛАВНОЕ МЕНЮ
# ============================================================

def main_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Общение",
                callback_data="chat"
            )
        ],
        [
            InlineKeyboardButton(
                "🤖 О Вась AI",
                callback_data="about"
            )
        ],
        [
            InlineKeyboardButton(
                "👤 Автор",
                callback_data="author"
            )
        ],
        [
            InlineKeyboardButton(
                "❤️ Поддержать автора",
                callback_data="support"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "✨ Вас приветствует Вась AI ✨\n\n"
        "Твой простой ИИ-помощник прямо в Telegram 🤖"
    )

    keyboard = main_keyboard()

    try:
        if os.path.exists(START_IMAGE):

            with open(START_IMAGE, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard
                )

        else:

            await update.message.reply_text(
                text + "\n\n🐱 Файл kot.jpg не найден.",
                reply_markup=keyboard
            )

    except Exception as e:
        print("START ERROR:", e)

        await update.message.reply_text(
            text,
            reply_markup=keyboard
        )


# ============================================================
# 🔘 КНОПКИ
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data == "chat":

        await query.message.reply_text(
            "💬 Режим общения включён!\n\n"
            "Вась AI уже здесь 👇\n\n"
            "Привет! 👋"
        )

    elif query.data == "about":

        await query.message.reply_text(
            "🤖 О Вась AI\n\n"
            "Вась AI — простой искусственный интеллект "
            "для общения, ответов на вопросы и помощи "
            "с разными задачами.\n\n"
            "Постепенно он будет становиться умнее 🚀"
        )

    elif query.data == "author":

        await query.message.reply_text(
            "👤 Автор\n\n"
            "@youngallah — гений, филантроп, миллиардер 😎"
        )

    elif query.data == "support":

        await query.message.reply_text(
            "❤️ Поддержать автора\n\n"
            "Пока еще в разработке 🛠️"
        )


# ============================================================
# 💬 СООБЩЕНИЯ
# ============================================================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text

    # Показываем, что бот печатает
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    answer = await ask_ai(user_id, text)

    await update.message.reply_text(answer)


# ============================================================
# 🗑️ /RESET
# ============================================================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    clear_history(user_id)

    await update.message.reply_text(
        "🧠 Память очищена!\n\n"
        "Начинаем общение с чистого листа."
    )


# ============================================================
# 🚀 ЗАПУСК
# ============================================================

def main():

    init_db()

    print("================================")
    print("🤖 Вась AI запускается...")
    print("================================")

    if BOT_TOKEN.startswith("ВСТАВЬ"):
        print("❌ Ты не вставил BOT_TOKEN!")

    if GROQ_API_KEY.startswith("ВСТАВЬ"):
        print("❌ Ты не вставил GROQ_API_KEY!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )

    print("✅ Вась AI запущен!")
    print("Нажми Ctrl+C для остановки.")

    app.run_polling()


if __name__ == "__main__":
    main()