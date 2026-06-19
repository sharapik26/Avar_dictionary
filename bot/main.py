"""
Основной скрипт Telegram-бота для Аварского словаря.
Содержит обработчики команд, поиск слов, планировщик рассылок
и интеграцию с Telegram WebApp.
"""
# flake8: noqa: E402, E501

import json
import os
import sys

# Добавляем путь к API модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import logging
from datetime import time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    BotCommand,
    MenuButtonWebApp,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, WEBAPP_URL, SUBSCRIBERS_FILE, DATA_DIR, PROXY_URL
from dictionary import DictionaryManager

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Загрузка словарей
dict_manager = DictionaryManager(DATA_DIR)


# ──────────────────────────────────────────────
# Работа с подписчиками
# ──────────────────────────────────────────────

def load_subscribers() -> set:
    """Загрузить список подписчиков из файла."""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def save_subscribers(subscribers: set):
    """Сохранить список подписчиков в файл."""
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subscribers), f)


# ──────────────────────────────────────────────
# Форматирование словарных статей
# ──────────────────────────────────────────────

def format_entry(entry: dict, detailed: bool = False) -> str:
    """Форматировать словарную статью для Telegram."""
    word = entry.get("word", "?")
    pos = entry.get("pos", "")
    senses = entry.get("senses", [])
    forms = entry.get("forms", [])

    lines = []
    lines.append(f"📖 *{escape_md(word)}*")

    if pos:
        lines.append(f"_{escape_md(pos)}_")

    lines.append("")

    for i, sense in enumerate(senses):
        text = sense.get("text", "")
        comment = sense.get("comment", "")
        labels = sense.get("labels", [])

        if text:
            prefix = f"{i+1}\\. " if len(senses) > 1 else ""
            label_str = ""
            if labels:
                label_str = f" _\\({escape_md(', '.join(labels))}\\)_"
            lines.append(f"{prefix}{escape_md(text)}{label_str}")

            if comment:
                lines.append(f"   💬 _{escape_md(comment)}_")

        # Примеры
        examples = sense.get("examples", [])
        if examples and detailed:
            for ex in examples[:3]:  # Максимум 3 примера
                av = ex.get("av", "")
                ru = ex.get("ru", "")
                if av and ru:
                    lines.append(f"   ▸ {escape_md(av)}")
                    lines.append(f"     _{escape_md(ru)}_")
        elif examples and not detailed:
            ex = examples[0]
            av = ex.get("av", "")
            ru = ex.get("ru", "")
            if av and ru:
                lines.append(f"   ▸ {escape_md(av)}")
                lines.append(f"     _{escape_md(ru)}_")

    # Формы слова (только в детальном режиме)
    if detailed and forms and len(forms) > 1:
        lines.append("")
        lines.append(f"📝 *Формы:* {escape_md(', '.join(forms))}")

    return "\n".join(lines)


def escape_md(text: str) -> str:
    """Экранировать специальные символы MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


# ──────────────────────────────────────────────
# Обработчики команд
# ──────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    keyboard = []

    # Кнопка Mini App
    if WEBAPP_URL and WEBAPP_URL != "https://your-domain.com":
        keyboard.append([
            InlineKeyboardButton(
                "📖 Открыть словарь",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🎲 Случайное слово", callback_data="random_word"),
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    av_len = len(dict_manager.dictionaries.get('av-ru', {}).entries if dict_manager.dictionaries.get('av-ru') else [])
    ru_len = len(dict_manager.dictionaries.get('ru-av', {}).entries if dict_manager.dictionaries.get('ru-av') else [])
    welcome_text = (
        "🏔 *Добро пожаловать\\!*\n\n"
        "Я бот для изучения *аварского языка* \\(магӀарул мацӀ\\)\\.\n\n"
        "🔍 Отправьте мне слово — и я найду перевод\n"
        "🎲 /word — случайное слово с примером\n"
        "📅 /subscribe — подписка на «слово дня»\n"
        "📖 Используйте кнопку ниже для полного словаря\n\n"
        f"📚 В базе: *{escape_md(str(av_len))}* "
        f"аварских и *{escape_md(str(ru_len))}* "
        "русских статей"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


async def word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /word — случайное слово."""
    entry = dict_manager.get_random("av-ru")
    message = update.message or update.callback_query.message
    
    if entry is None:
        await message.reply_text("❌ Словарь не загружен.")
        return

    text = format_entry(entry, detailed=True)
    text = f"🎲 *Случайное слово:*\n\n{text}"

    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def random_word_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн кнопки 'Случайное слово'."""
    await update.callback_query.answer()
    await word_command(update, context)


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /subscribe."""
    subscribers = load_subscribers()
    chat_id = update.effective_chat.id

    if chat_id in subscribers:
        await update.message.reply_text(
            "✅ Вы уже подписаны на «слово дня»\\!\n"
            "Каждый день в 10:00 \\(МСК\\) вы будете получать новое аварское слово\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        subscribers.add(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text(
            "🎉 Вы подписались на «слово дня»\\!\n\n"
            "Каждый день в *10:00* \\(МСК\\) вы будете получать новое аварское слово с переводом и примером\\.\n\n"
            "Для отписки: /unsubscribe",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /unsubscribe."""
    subscribers = load_subscribers()
    chat_id = update.effective_chat.id

    if chat_id in subscribers:
        subscribers.discard(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text(
            "👋 Вы отписались от «слова дня»\\.\n"
            "Чтобы подписаться снова: /subscribe",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            "ℹ️ Вы не были подписаны на «слово дня»\\.\n"
            "Чтобы подписаться: /subscribe",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений — поиск слова."""
    query = update.message.text.strip()
    if not query or len(query) > 100:
        return

    # Ищем сначала в аварско-русском, потом в русско-аварском
    results = dict_manager.search(query, "av-ru", limit=3)
    dict_label = "🇦🇿→🇷🇺"

    if not results:
        results = dict_manager.search(query, "ru-av", limit=3)
        dict_label = "🇷🇺→🇦🇿"

    if not results:
        await update.message.reply_text(
            f"🔍 По запросу «{escape_md(query)}» ничего не найдено\\.\n\n"
            "Попробуйте другое написание или откройте словарь для расширенного поиска\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    lines = [f"🔍 Результаты {dict_label} для «{escape_md(query)}»:\n"]
    for entry in results:
        lines.append(format_entry(entry, detailed=False))
        lines.append("")

    if len(results) >= 3:
        lines.append("_Показаны первые 3 результата\\. Для полного поиска откройте словарь\\._")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# ──────────────────────────────────────────────
# Ежедневная рассылка «Слово дня»
# ──────────────────────────────────────────────

async def send_word_of_day(context: ContextTypes.DEFAULT_TYPE):
    """Отправить 'слово дня' всем подписчикам."""
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("Нет подписчиков для рассылки слова дня.")
        return

    entry = dict_manager.get_random("av-ru")
    if entry is None:
        logger.error("Не удалось получить случайное слово.")
        return

    text = f"🌅 *Слово дня:*\n\n{format_entry(entry, detailed=True)}"

    sent_count = 0
    failed = []

    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            sent_count += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить слово дня в чат {chat_id}: {e}")
            failed.append(chat_id)

    # Удалить невалидные чаты
    if failed:
        subscribers -= set(failed)
        save_subscribers(subscribers)

    logger.info(f"Слово дня отправлено {sent_count} подписчикам.")


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────

async def post_init(application: Application):
    """Настройка команд бота и кнопки Mini App."""
    await application.bot.set_my_commands([
        BotCommand("start", "Главное меню и словарь"),
        BotCommand("word", "Случайное слово"),
        BotCommand("subscribe", "Подписаться на рассылку"),
        BotCommand("unsubscribe", "Отписаться от рассылки")
    ])

    if WEBAPP_URL and WEBAPP_URL != "https://your-domain.com":
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Словарь", web_app=WebAppInfo(url=WEBAPP_URL))
        )

def get_bot_app() -> Application | None:
    """Создает и настраивает экземпляр бота."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("=" * 50)
        print("ОШИБКА: Установите токен бота!")
        print("=" * 50)
        return None

    # Создание приложения
    builder = Application.builder().token(BOT_TOKEN).post_init(post_init)
    if PROXY_URL:
        builder = builder.proxy_url(PROXY_URL).get_updates_proxy_url(PROXY_URL)
    app = builder.build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("word", word_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CallbackQueryHandler(random_word_callback, pattern="^random_word$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Планировщик слова дня
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(
            send_word_of_day,
            time=time(hour=7, minute=0),  # UTC (МСК - 3)
            name="word_of_day",
        )
        logger.info("Запланирована ежедневная рассылка слова дня в 10:00 МСК")

    return app

def main():
    """Запуск бота автономно."""
    app = get_bot_app()
    if app:
        logger.info("Бот запущен автономно!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
