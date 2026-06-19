"""
Конфигурация Telegram-бота.
"""

import os

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# URL Mini App (заменить на реальный при деплое)
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://hybrid-wage-devel-chicago.trycloudflare.com")

# Файл для хранения подписчиков
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")

# Время отправки слова дня (МСК = UTC+3)
WORD_OF_DAY_HOUR = 9  # 09:00
WORD_OF_DAY_MINUTE = 0

# Путь к словарям
DATA_DIR = os.path.join(os.path.dirname(__file__), "..")

# Прокси для доступа к Telegram API (если API заблокирован)
# Форматы: "http://host:port", "socks5://host:port", "http://user:pass@host:port"
# Оставьте None если прокси не нужен
PROXY_URL = os.environ.get("PROXY_URL", None)
