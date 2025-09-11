import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Загружаем токены
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Создаём клиент OpenAI для Hugging Face
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здравствуйте, Александр! Я твой личный помощник JARVIS. У меня пока небольшой функционал, но я развиваюсь. Спрашивай, что тебя интересует.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:together",
            messages=[
                {"role": "user", "content": user_text}
            ],
        )
        # Правильный способ получить текст ответа
        reply = completion.choices[0].message.content
    except Exception as e:
        reply = f"Ошибка при запросе к модели: {e}"

    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
