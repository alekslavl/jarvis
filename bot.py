import os
import json
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
from openai import OpenAI

# --- Загружаем токены ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "data.json"
LOG_FILE = "bot_log.txt"
VOICE_DIR = "voices"

# --- Логирование ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

def log(user_id, action, message=""):
    logging.info(f"User {user_id}: {action} {message}")

# --- Работа с JSON ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Главное меню (инлайн-кнопки) ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("💱 Конвертер валют", callback_data="convert")],
        [InlineKeyboardButton("🌤 Погода", callback_data="weather")],
        [InlineKeyboardButton("📝 Напоминания", callback_data="notes")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    data[user_id] = {"menu": "main", "notes": data.get(user_id, {}).get("notes", [])}
    save_data(data)
    log(user_id, "Запустил бота")
    await update.message.reply_text(
        "Привет, Александр! Тебя приветствует твой личный помощник J.A.R.V.I.S. Выбери действие:",
        reply_markup=main_menu()
    )

# --- /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 Доступные команды:\n\n"
        "/start - Главное меню\n"
        "/help - Список команд\n"
        "/convert - Конвертер валют\n"
        "/list - Показать заметки\n"
        "/del <номер> - Удалить заметку\n"
        "/voices - Посмотреть голосовые сообщения\n\n"
        "👉 Также можно пользоваться кнопками меню."
    )
    await update.message.reply_text(help_text, reply_markup=ReplyKeyboardRemove())

# --- Конвертер валют ---
def convert_currency(amount: float, from_currency: str, to_currency: str):
    if not EXCHANGE_API_KEY:
        return None
    url = (
        "http://api.currencylayer.com/convert"
        f"?from={from_currency}&to={to_currency}&amount={amount}&access_key={EXCHANGE_API_KEY}"
    )
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        print("Currency API response:", data)
        if data.get("success") and "result" in data:
            rate = data.get("info", {}).get("quote")
            return data["result"], rate
        return None
    except Exception as e:
        print("Ошибка API валют:", e)
        return None

# --- Погода ---
def get_weather(city_name):
    if not OPENWEATHER_API_KEY:
        return None
    url = (
        f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    )
    try:
        resp = requests.get(url)
        data = resp.json()
        if data.get("cod") != 200:
            return None
        weather_desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        return f"Погода в {city_name}:\n{weather_desc}\n🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n💧 Влажность: {humidity}%\n💨 Ветер: {wind_speed} м/с"
    except Exception as e:
        print("Ошибка API погоды:", e)
        return None

# --- /convert ---
async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    data[user_id]["menu"] = "convert"
    save_data(data)
    await update.message.reply_text(
        "💱 Конвертер валют\n\n"
        "Напиши в формате: `<сумма> <из валюты> <в валюту>`\nПример: `100 USD RUB`\n\n"
        "Чтобы выйти из режима конвертации — /start",
        reply_markup=ReplyKeyboardRemove()
    )

# --- Просмотр заметок ---
async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    notes = data.get(user_id, {}).get("notes", [])
    if notes:
        text = "📝 Твои заметки:\n" + "\n".join([f"{i+1}. {note}" for i, note in enumerate(notes)])
    else:
        text = "📝 Заметок пока нет."
    await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

# --- Удаление заметки ---
async def del_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    notes = data.get(user_id, {}).get("notes", [])
    if not notes:
        await update.message.reply_text("⚠️ Заметок нет.", reply_markup=ReplyKeyboardRemove())
        return

    try:
        idx = int(context.args[0]) - 1
        if 0 <= idx < len(notes):
            removed = notes.pop(idx)
            save_data(data)
            await update.message.reply_text(f"✅ Удалена заметка: {removed}", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("⚠️ Неверный номер заметки.", reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("⚠️ Используй команду: /del <номер заметки>", reply_markup=ReplyKeyboardRemove())

# --- Просмотр голосовых сообщений ---
async def list_voices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_dir = os.path.join(VOICE_DIR, user_id)
    if not os.path.exists(user_dir):
        await update.message.reply_text("⚠️ Голосовых сообщений нет.", reply_markup=ReplyKeyboardRemove())
        return

    files = sorted(os.listdir(user_dir))
    if not files:
        await update.message.reply_text("⚠️ Голосовых сообщений нет.", reply_markup=ReplyKeyboardRemove())
        return

    for f in files:
        path = os.path.join(user_dir, f)
        await update.message.reply_voice(voice=InputFile(path))

# --- Команда /ask ---
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Используй команду так: /ask <твой вопрос>")
        return

    question = " ".join(context.args)
    await update.message.reply_text("🤖 Думаю...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты — Джарвис, умный ассистент как у Тони Старка."},
                {"role": "user", "content": question},
            ],
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
    except Exception as e:
        print("Ошибка OpenAI:", e)
        await update.message.reply_text("⚠️ Не удалось получить ответ от ИИ.")

# --- Обработка сообщений ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    menu_state = data.get(user_id, {}).get("menu", "main")
    text = update.message.text.strip() if update.message.text else ""
    log(user_id, "Написал сообщение", text if text else "[non-text]")

    # --- Голосовые сообщения ---
    if update.message.voice:
        user_dir = os.path.join(VOICE_DIR, user_id)
        os.makedirs(user_dir, exist_ok=True)

        file_id = update.message.voice.file_id
        new_file = await context.bot.get_file(file_id)
        file_path = os.path.join(user_dir, f"{file_id}.ogg")
        await new_file.download_to_drive(file_path)

        await update.message.reply_text(
            f"✅ Голосовое сообщение сохранено ({len(os.listdir(user_dir))} всего).",
            reply_markup=ReplyKeyboardRemove()
        )
        log(user_id, "Сохранил голосовое сообщение", file_path)
        return

    # --- Проверка на ИИ (триггер-слово "джарвис") ---
    if text.lower().startswith("джарвис"):
        question = text[len("джарвис"):].strip()
        await update.message.reply_text("🤖 Джарвис думает...")
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты — Джарвис, умный ассистент как у Тони Старка."},
                    {"role": "user", "content": question},
                ],
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(answer)
        except Exception as e:
            print("Ошибка OpenAI:", e)
            await update.message.reply_text("⚠️ Не удалось получить ответ от Джарвиса.")
        return

    # --- Конвертер валют ---
    if menu_state == "convert":
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("⚠️ Формат: `<сумма> <из валюты> <в валюту>`", reply_markup=ReplyKeyboardRemove())
            return
        try:
            amount = float(parts[0])
            from_cur = parts[1].upper()
            to_cur = parts[2].upper()
            conv = convert_currency(amount, from_cur, to_cur)
            if conv:
                result, rate = conv
                await update.message.reply_text(
                    f"💱 {amount} {from_cur} = {result:.2f} {to_cur}\n"
                    f"(Курс: 1 {from_cur} = {rate:.6f} {to_cur})",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await update.message.reply_text("⚠️ Ошибка конвертации. Проверь валюты или API-ключ.", reply_markup=ReplyKeyboardRemove())
        except:
            await update.message.reply_text("⚠️ Ошибка. Попробуй ещё раз.", reply_markup=ReplyKeyboardRemove())
        return

    # --- Погода ---
    if menu_state == "weather":
        city = text
        weather_info = get_weather(city)
        if weather_info:
            await update.message.reply_text(weather_info, reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("⚠️ Не удалось получить погоду. Проверь название города.", reply_markup=ReplyKeyboardRemove())
        return

    # --- Заметки ---
    if menu_state == "notes":
        if text.startswith("/"):
            return
        data[user_id]["notes"].append(text)
        save_data(data)
        await update.message.reply_text(f"✅ Заметка добавлена: {text}", reply_markup=ReplyKeyboardRemove())
        return

    # --- Авто-Джарвис: любое другое сообщение ---
    if text:
        question = text
        await update.message.reply_text("🤖 Джарвис думает...")
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты — Джарвис, умный ассистент как у Тони Старка."},
                    {"role": "user", "content": question},
                ],
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(answer)
        except Exception as e:
            print("Ошибка OpenAI:", e)
            await update.message.reply_text("⚠️ Не удалось получить ответ от Джарвиса.")

# --- Кнопки меню ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()

    if query.data == "convert":
        data[user_id]["menu"] = "convert"
        save_data(data)
        await query.edit_message_text("💱 Конвертер валют\n\nНапиши в формате: `<сумма> <из валюты> <в валюту>`")
    elif query.data == "weather":
        data[user_id]["menu"] = "weather"
        save_data(data)
        await query.edit_message_text("🌤 Введите город, чтобы узнать погоду:")
    elif query.data == "notes":
        data[user_id]["menu"] = "notes"
        if "notes" not in data[user_id]:
            data[user_id]["notes"] = []
        save_data(data)
        await query.edit_message_text(
            "📝 Режим Напоминаний.\n"
            "Добавь новую заметку, напиши /list для просмотра заметок или /del для удаления."
        )

# --- Создаём папку для голосов ---
os.makedirs(VOICE_DIR, exist_ok=True)

# --- Запуск ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(CommandHandler("list", list_notes))
    app.add_handler(CommandHandler("del", del_note))
    app.add_handler(CommandHandler("voices", list_voices))
    app.add_handler(CommandHandler("ask", ask_ai))

    # Обработка кнопок меню
    app.add_handler(CallbackQueryHandler(button))

    # Обработка сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.add_handler(MessageHandler(filters.VOICE, echo))  # голосовые сообщения

    # Запуск бота
    app.run_polling()

if __name__ == "__main__":
    main()
