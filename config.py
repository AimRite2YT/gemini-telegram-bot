# Файл: config.py

GEMINI_API_KEY = 'ENTER YOUR GEMINI API KEY'
TELEGRAM_BOT_TOKEN = 'ENTER YOUR TELEGRAM BOT TOKEN'

# ID администраторов (твой Telegram user_id)
ADMIN_IDS = []  # Пример: [123456789, 987654321]

# Ограничение запросов (rate limiting)
MAX_REQUESTS_PER_MINUTE = 10  # Макс. запросов в минуту на одного пользователя

# История сообщений
MAX_HISTORY_LENGTH = 50  # Разумное кол-во для контекста

# Системный промпт по умолчанию
DEFAULT_SYSTEM_PROMPT = "Ты - умный и полезный AI-ассистент. Отвечай чётко и по делу. Если вопрос на русском — отвечай на русском."
