"""
Конфигурация Telegram-бота и системных переменных.
"""

import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-domain.com")

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:Sharapudin1.@db.wzvwsfrqhgishbwoxcfn.supabase.co:5432/postgres"
)

WORD_OF_DAY_HOUR = 10
WORD_OF_DAY_MINUTE = 0

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")

PROXY_URL = os.environ.get("PROXY_URL", None)
