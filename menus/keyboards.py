from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👋 Приветствия", callback_data="menu_greetings")],
        [InlineKeyboardButton("ℹ️ Инфо", callback_data="menu_info")],
        [InlineKeyboardButton("🌍 Google", url="https://google.com")]
    ])

def greetings_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Сказать привет 👋", callback_data="say_hello")],
        [InlineKeyboardButton("Как дела? 😊", callback_data="ask_how")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])

def info_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("О боте 🤖", callback_data="about_bot")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])
