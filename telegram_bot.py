# Файл: telebot_script.py
import telebot
import datetime
from config import TELEGRAM_BOT_TOKEN
from gemini_api import generate_gemini_response, set_gemini_model

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# История твоих глупостей
user_histories = {}
MAX_HISTORY_LENGTH = 666  # Число дьявола

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Я - Gemini-бот. Используй /ask <вопрос>, чтобы узнать что-то.");

@bot.message_handler(commands=['ask'])
def ask_command(message):
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Получаем твой жалкий вопрос
    try:
        prompt = message.text.split(' ', 1)[1]
    except IndexError:
        bot.reply_to(message, "Ты забыл задать вопрос после /ask.");
        return

    with open("messages_logger.txt", "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - ID: {user_id}, Имя: {first_name} {last_name} (@{username}), Сообщение: {message.text}\n")

    # История твоих ошибок
    if user_id in user_histories:
        history = user_histories[user_id]
    else:
        history = []

    # Создаем контекст для ответа (который ты все равно не поймешь)
    context = "\n".join([f"User: {q}\nGemini: {a}" for q, a in history])
    full_prompt = f"{context}\nUser: {prompt}\nGemini:"

    # Получаем ответ от Gemini (если он захочет)
    response_text = generate_gemini_response(full_prompt)

    # Проверяем, является ли ответ кодом
    if "```" not in response_text:
        if "import" in response_text or "def" in response_text or "class" in response_text:
             response_text = "```python\n" + response_text + "\n```" # Форматируем как код, если похоже на код
    # Добавляем вопрос и ответ в историю (чтобы помнить твои глупости)
    history.append((prompt, response_text))
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
    user_histories[user_id] = history

    bot.reply_to(message, response_text, parse_mode="Markdown") # Включаем поддержку Markdown

@bot.message_handler(commands=['model'])
def model_command(message):
    try:
        model_name = message.text.split(' ', 1)[1]
        result = set_gemini_model(model_name)
        bot.reply_to(message, result)
    except IndexError:
        bot.reply_to(message, "Ты забыл указать название модели после /model.");
    except ValueError as e:
        bot.reply_to(message, str(e))

@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.reply_to_message.from_user.id == bot.get_me().id)
def reply_handler(message):
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Получаем твой жалкий вопрос
    prompt = message.text

    with open("messages_logger.txt", "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - ID: {user_id}, Имя: {first_name} {last_name} (@{username}), Reply to bot, Сообщение: {message.text}\n")

    # История твоих ошибок
    if user_id in user_histories:
        history = user_histories[user_id]
    else:
        history = []

    # Добавляем в контекст сообщение, на которое отвечаем
    replied_message_text = message.reply_to_message.text
    context = f"Предыдущее сообщение от бота: {replied_message_text}\n" + "\n".join([f"User: {q}\nGemini: {a}" for q, a in history])
    full_prompt = f"{context}\nUser: {prompt}\nGemini:"

    # Получаем ответ от Gemini (если он захочет)
    response_text = generate_gemini_response(full_prompt)
     # Проверяем, является ли ответ кодом
    if "```" not in response_text:
        if "import" in response_text or "def" in response_text or "class" in response_text:
             response_text = "```python\n" + response_text + "\n```" # Форматируем как код, если похоже на код

    # Добавляем вопрос и ответ в историю (чтобы помнить твои глупости)
    history.append((prompt, response_text))
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
    user_histories[user_id] = history

    bot.reply_to(message, response_text, parse_mode="Markdown")


def start_bot():
    try:
        bot.infinity_polling()
        print("Бот ждет твоих вопросов (но не факт, что ответит).")
    except Exception as e:
        print(f"Бот сломался: {e}")

if __name__ == "__main__":
    start_bot()