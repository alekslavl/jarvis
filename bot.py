import os
import json
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

# --- Загружаем токены ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

DATA_FILE = "data.json"
LOG_FILE = "bot_log.txt"

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

# --- Главное меню (только инлайн) ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("💱 Конвертер валют", callback_data="convert")],
        [InlineKeyboardButton("🌤 Погода", callback_data="weather")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    data[user_id] = {"menu": "main"}
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
        "/convert - Конвертер валют\n\n"
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

# --- Обработка сообщений ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    menu_state = data.get(user_id, {}).get("menu", "main")
    log(user_id, "Написал сообщение", update.message.text)

    # --- Конвертация валют ---
    if menu_state == "convert":
        parts = update.message.text.strip().split()
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
        city = update.message.text.strip()
        weather_info = get_weather(city)
        if weather_info:
            await update.message.reply_text(weather_info, reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text("⚠️ Не удалось получить погоду. Проверь название города.", reply_markup=ReplyKeyboardRemove())
        return

    # --- Обычное сообщение ---
    await update.message.reply_text(f"Ты в меню '{menu_state}'. Ты написал: {update.message.text}", reply_markup=ReplyKeyboardRemove())

# --- Кнопки меню ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()

    if query.data == "hello":
        await query.edit_message_text("Привет! 👋")
    elif query.data == "info":
        await query.edit_message_text("ℹ️ Я учебный бот для практики Python и Telegram API.")
    elif query.data == "convert":
        data[user_id]["menu"] = "convert"
        save_data(data)
        await query.edit_message_text("💱 Конвертер валют\n\nНапиши в формате: `<сумма> <из валюты> <в валюту>`")
    elif query.data == "weather":
        data[user_id]["menu"] = "weather"
        save_data(data)
        await query.edit_message_text("🌤 Введите город, чтобы узнать погоду:")

# --- Запуск ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()

if __name__ == "__main__":
    main()
