# Файл: telegram_bot.py
# Улучшенная версия Gemini Telegram Bot

import telebot
import datetime
import time
import json
import os
from collections import defaultdict, deque
from telebot import types

from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, MAX_REQUESTS_PER_MINUTE, MAX_HISTORY_LENGTH, DEFAULT_SYSTEM_PROMPT
from gemini_api import (
    generate_gemini_response,
    generate_gemini_vision_response,
    set_gemini_model,
    get_current_model,
    get_models_list
)

# ──────────────────────────────────────────
# Инициализация бота
# ──────────────────────────────────────────
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ──────────────────────────────────────────
# Хранилища данных (в памяти)
# ──────────────────────────────────────────
user_histories = {}          # история диалогов: {user_id: [(q, a), ...]}
user_system_prompts = {}     # системные промпты: {user_id: str}
user_stats = defaultdict(lambda: {"requests": 0, "joined": None})  # статистика
rate_limit_tracker = defaultdict(deque)   # rate limiting: {user_id: deque of timestamps}

# ──────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────

def log_message(user, text: str, extra: str = ""):
    """Логирует сообщение пользователя в файл."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"@{user.username}" if user.username else "no_username"
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    line = f"[{now}] ID:{user.id} {name} ({username}){' | ' + extra if extra else ''} → {text}\n"
    with open("messages_logger.txt", "a", encoding="utf-8") as f:
        f.write(line)


def is_rate_limited(user_id: int) -> bool:
    """Проверяет, не превысил ли пользователь лимит запросов."""
    now = time.time()
    timestamps = rate_limit_tracker[user_id]
    # Убираем старые записи (старше 60 секунд)
    while timestamps and now - timestamps[0] > 60:
        timestamps.popleft()
    if len(timestamps) >= MAX_REQUESTS_PER_MINUTE:
        return True
    timestamps.append(now)
    return False


def get_user_history(user_id: int) -> list:
    """Возвращает историю диалога пользователя."""
    return user_histories.get(user_id, [])


def update_user_history(user_id: int, question: str, answer: str):
    """Добавляет запись в историю и обрезает до MAX_HISTORY_LENGTH."""
    history = user_histories.get(user_id, [])
    history.append((question, answer))
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
    user_histories[user_id] = history


def build_context(user_id: int, prompt: str) -> str:
    """Строит полный контекст для отправки в Gemini."""
    history = get_user_history(user_id)
    context_parts = [f"User: {q}\nAssistant: {a}" for q, a in history]
    context = "\n".join(context_parts)
    return f"{context}\nUser: {prompt}\nAssistant:" if context else f"User: {prompt}\nAssistant:"


def get_system_prompt(user_id: int) -> str:
    """Возвращает системный промпт пользователя."""
    return user_system_prompts.get(user_id, DEFAULT_SYSTEM_PROMPT)


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id in ADMIN_IDS


def send_typing(chat_id):
    """Отправляет действие 'печатает...'."""
    bot.send_chat_action(chat_id, 'typing')


# ──────────────────────────────────────────
# Команды
# ──────────────────────────────────────────

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    if user_stats[user.id]["joined"] is None:
        user_stats[user.id]["joined"] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📋 Помощь", callback_data="help"),
        types.InlineKeyboardButton("🤖 Модели", callback_data="models_list")
    )
    
    bot.reply_to(message,
        f"👋 Привет, *{user.first_name}*!\n\n"
        f"Я — Gemini AI Бот. Ты можешь:\n"
        f"• Просто написать мне сообщение\n"
        f"• Отправить фото с вопросом\n"
        f"• Использовать команды\n\n"
        f"Текущая модель: `{get_current_model()}`\n\n"
        f"Напиши /help для списка всех команд.",
        parse_mode="Markdown",
        reply_markup=markup
    )
    log_message(user, "/start")


@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "📖 *Список команд:*\n\n"
        "*Основные:*\n"
        "• Просто напиши сообщение — бот ответит\n"
        "• Отправь фото с подписью — бот проанализирует\n"
        "• `/ask <вопрос>` — задать вопрос явно\n\n"
        "*Управление:*\n"
        "• `/clear` — очистить историю диалога\n"
        "• `/history` — показать статистику истории\n"
        "• `/stats` — твоя статистика\n\n"
        "*Настройки:*\n"
        "• `/model <название>` — сменить модель\n"
        "• `/models` — список доступных моделей\n"
        "• `/setprompt <текст>` — установить системный промпт\n"
        "• `/resetprompt` — сбросить промпт на стандартный\n"
        "• `/myprompt` — показать текущий промпт\n\n"
        "*Информация:*\n"
        "• `/currentmodel` — текущая модель\n"
        "• `/start` — приветствие\n"
        "• `/help` — это сообщение\n"
    )
    if is_admin(message.from_user.id):
        help_text += "\n*Админ:*\n• `/broadcast <текст>` — рассылка всем пользователям\n"
    
    bot.reply_to(message, help_text, parse_mode="Markdown")


@bot.message_handler(commands=['ask'])
def cmd_ask(message):
    user = message.from_user
    
    if is_rate_limited(user.id):
        bot.reply_to(message, f"⏳ Слишком много запросов. Подожди минуту.\n(Лимит: {MAX_REQUESTS_PER_MINUTE} в минуту)")
        return
    
    try:
        prompt = message.text.split(' ', 1)[1].strip()
    except IndexError:
        bot.reply_to(message, "❓ Укажи вопрос после команды.\nПример: `/ask Как дела?`", parse_mode="Markdown")
        return
    
    if not prompt:
        bot.reply_to(message, "❓ Вопрос не может быть пустым.")
        return
    
    log_message(user, prompt, extra="/ask")
    send_typing(message.chat.id)
    
    full_prompt = build_context(user.id, prompt)
    sys_prompt = get_system_prompt(user.id)
    response_text = generate_gemini_response(full_prompt, sys_prompt)
    
    update_user_history(user.id, prompt, response_text)
    user_stats[user.id]["requests"] += 1
    
    bot.reply_to(message, response_text, parse_mode="Markdown")


@bot.message_handler(commands=['clear'])
def cmd_clear(message):
    user_id = message.from_user.id
    count = len(user_histories.get(user_id, []))
    user_histories[user_id] = []
    bot.reply_to(message, f"🗑 История очищена. Удалено {count} сообщений.")


@bot.message_handler(commands=['history'])
def cmd_history(message):
    user_id = message.from_user.id
    history = get_user_history(user_id)
    count = len(history)
    
    if count == 0:
        bot.reply_to(message, "📭 История пуста.")
        return
    
    # Показываем последние 3 записи
    preview = ""
    for q, a in history[-3:]:
        q_short = q[:50] + "..." if len(q) > 50 else q
        preview += f"\n👤 {q_short}\n"
    
    bot.reply_to(message,
        f"📚 *История диалога:*\n"
        f"Всего записей: {count}/{MAX_HISTORY_LENGTH}\n\n"
        f"*Последние сообщения:*{preview}\n\n"
        f"Используй /clear чтобы очистить.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['models'])
def cmd_models(message):
    models = get_models_list()
    current = get_current_model()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key in models:
        label = f"✅ {key}" if key == current else key
        markup.add(types.InlineKeyboardButton(label, callback_data=f"set_model_{key}"))
    
    text = "🤖 *Доступные модели:*\n\n"
    for key, full in models.items():
        marker = "▶️" if key == current else "•"
        text += f"{marker} `{key}`\n   {full}\n\n"
    text += f"Текущая: `{current}`"
    
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=['model'])
def cmd_model(message):
    try:
        model_name = message.text.split(' ', 1)[1].strip()
        result = set_gemini_model(model_name)
        bot.reply_to(message, result, parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "❓ Укажи название модели.\nПример: `/model gemini-2.0-flash`\n\nСписок: /models", parse_mode="Markdown")
    except ValueError as e:
        bot.reply_to(message, str(e), parse_mode="Markdown")


@bot.message_handler(commands=['currentmodel'])
def cmd_currentmodel(message):
    from gemini_api import AVAILABLE_MODELS
    key = get_current_model()
    full = AVAILABLE_MODELS.get(key, key)
    bot.reply_to(message, f"🤖 Текущая модель:\n• Ключ: `{key}`\n• Полное название: `{full}`", parse_mode="Markdown")


@bot.message_handler(commands=['setprompt'])
def cmd_setprompt(message):
    user_id = message.from_user.id
    try:
        prompt_text = message.text.split(' ', 1)[1].strip()
        if not prompt_text:
            raise IndexError
        user_system_prompts[user_id] = prompt_text
        bot.reply_to(message,
            f"✅ Системный промпт установлен:\n\n_{prompt_text}_",
            parse_mode="Markdown"
        )
    except IndexError:
        bot.reply_to(message,
            "❓ Укажи текст промпта после команды.\n"
            "Пример: `/setprompt Ты - пират и отвечаешь только на пиратском диалекте`",
            parse_mode="Markdown"
        )


@bot.message_handler(commands=['resetprompt'])
def cmd_resetprompt(message):
    user_id = message.from_user.id
    user_system_prompts.pop(user_id, None)
    bot.reply_to(message, f"✅ Промпт сброшен на стандартный:\n\n_{DEFAULT_SYSTEM_PROMPT}_", parse_mode="Markdown")


@bot.message_handler(commands=['myprompt'])
def cmd_myprompt(message):
    user_id = message.from_user.id
    prompt = get_system_prompt(user_id)
    is_custom = user_id in user_system_prompts
    label = "🔧 Кастомный" if is_custom else "📋 Стандартный"
    bot.reply_to(message, f"{label} промпт:\n\n_{prompt}_", parse_mode="Markdown")


@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    user = message.from_user
    stats = user_stats[user.id]
    history_count = len(get_user_history(user.id))
    joined = stats["joined"] or "неизвестно"
    
    bot.reply_to(message,
        f"📊 *Твоя статистика:*\n\n"
        f"👤 Имя: {user.first_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 Первый запрос: {joined}\n"
        f"💬 Всего запросов: {stats['requests']}\n"
        f"📚 Сообщений в истории: {history_count}/{MAX_HISTORY_LENGTH}\n"
        f"🤖 Текущая модель: `{get_current_model()}`\n"
        f"🔧 Промпт: {'кастомный' if user.id in user_system_prompts else 'стандартный'}",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────
# Админ-команды
# ──────────────────────────────────────────

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ У тебя нет прав администратора.")
        return
    
    try:
        broadcast_text = message.text.split(' ', 1)[1].strip()
    except IndexError:
        bot.reply_to(message, "❓ Укажи текст рассылки после /broadcast")
        return
    
    all_users = list(user_stats.keys())
    success = 0
    for uid in all_users:
        try:
            bot.send_message(uid, f"📢 *Сообщение от администратора:*\n\n{broadcast_text}", parse_mode="Markdown")
            success += 1
        except Exception:
            pass
    
    bot.reply_to(message, f"✅ Рассылка отправлена {success}/{len(all_users)} пользователям.")


# ──────────────────────────────────────────
# Обработка фото
# ──────────────────────────────────────────

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user = message.from_user
    
    if user_stats[user.id]["joined"] is None:
        user_stats[user.id]["joined"] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if is_rate_limited(user.id):
        bot.reply_to(message, f"⏳ Слишком много запросов. Подожди минуту.")
        return
    
    caption = message.caption or "Опиши это изображение подробно."
    log_message(user, f"[ФОТО] {caption}")
    send_typing(message.chat.id)
    
    # Получаем фото максимального размера
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    sys_prompt = get_system_prompt(user.id)
    response_text = generate_gemini_vision_response(caption, downloaded, "image/jpeg", sys_prompt)
    
    update_user_history(user.id, f"[Фото] {caption}", response_text)
    user_stats[user.id]["requests"] += 1
    
    bot.reply_to(message, response_text, parse_mode="Markdown")


# ──────────────────────────────────────────
# Обычные сообщения (без команды)
# ──────────────────────────────────────────

@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/'))
def handle_text(message):
    user = message.from_user
    
    if user_stats[user.id]["joined"] is None:
        user_stats[user.id]["joined"] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if is_rate_limited(user.id):
        bot.reply_to(message, f"⏳ Слишком много запросов. Подожди минуту.\n(Лимит: {MAX_REQUESTS_PER_MINUTE} в минуту)")
        return
    
    prompt = message.text.strip()
    if not prompt:
        return
    
    log_message(user, prompt)
    send_typing(message.chat.id)
    
    full_prompt = build_context(user.id, prompt)
    sys_prompt = get_system_prompt(user.id)
    response_text = generate_gemini_response(full_prompt, sys_prompt)
    
    update_user_history(user.id, prompt, response_text)
    user_stats[user.id]["requests"] += 1
    
    try:
        bot.reply_to(message, response_text, parse_mode="Markdown")
    except Exception:
        # Если Markdown не парсится — отправляем без форматирования
        bot.reply_to(message, response_text)


# ──────────────────────────────────────────
# Inline Callbacks (кнопки)
# ──────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "help":
        # Эмулируем /help
        cmd_help(call.message)
        bot.answer_callback_query(call.id)
    
    elif call.data == "models_list":
        cmd_models(call.message)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("set_model_"):
        model_key = call.data.replace("set_model_", "")
        try:
            result = set_gemini_model(model_key)
            bot.answer_callback_query(call.id, f"✅ Модель: {model_key}", show_alert=False)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=result,
                parse_mode="Markdown"
            )
        except ValueError as e:
            bot.answer_callback_query(call.id, str(e), show_alert=True)


# ──────────────────────────────────────────
# Запуск
# ──────────────────────────────────────────

def start_bot():
    print("🚀 Бот запущен! Нажми Ctrl+C для остановки.")
    print(f"🤖 Текущая модель: {get_current_model()}")
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=15)
    except KeyboardInterrupt:
        print("\n⛔ Бот остановлен.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    start_bot()
