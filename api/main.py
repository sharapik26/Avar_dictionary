"""
FastAPI сервер для аварского словаря.
Обслуживает API запросы и раздаёт статику Mini App.
"""
# flake8: noqa: E402, E501

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, ORJSONResponse
from pathlib import Path
from contextlib import asynccontextmanager
import sys

# Пути
BASE_DIR = Path(__file__).parent.parent
WEBAPP_DIR = BASE_DIR / "webapp"

sys.path.insert(0, str(BASE_DIR / "bot"))

from dictionary import DictionaryManager
from main import get_bot_app
from telegram import Update

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    bot_app = get_bot_app()
    if bot_app:
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        app.state.bot_app = bot_app
    yield
    # Shutdown
    if hasattr(app.state, "bot_app") and app.state.bot_app:
        bot_app = app.state.bot_app
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

# Инициализация приложения
app = FastAPI(
    title="МагӀарул мацӀ — Аварский словарь",
    description="API для аварско-русского и русско-аварского словаря",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Загрузка словарей
dict_manager = DictionaryManager(str(BASE_DIR))


@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    dict: str = Query("av-ru", pattern="^(av-ru|ru-av)$", description="Направление словаря"),
    limit: int = Query(50, ge=1, le=100, description="Максимум результатов"),
):
    """Поиск слов в словаре."""
    results = dict_manager.search(q, dict_name=dict, limit=limit)
    # Возвращаем облегчённые результаты для списка
    items = []
    for entry in results:
        senses = entry.get("senses", [])
        # Собираем краткий перевод
        translations = []
        for sense in senses:
            text = sense.get("text", "")
            if text:
                translations.append(text)
        
        items.append({
            "word": entry.get("word", ""),
            "pos": entry.get("pos", ""),
            "translation": "; ".join(translations[:2]) if translations else "",
            "has_examples": any(
                sense.get("examples") for sense in senses
            ),
        })
    return {"results": items, "total": len(items), "query": q, "dict": dict}


@app.get("/api/word/{word}")
async def get_word(
    word: str,
    dict: str = Query("av-ru", pattern="^(av-ru|ru-av)$"),
):
    """Получить полную статью слова."""
    entries = dict_manager.get_word(word, dict_name=dict)
    if not entries:
        return {"entries": [], "word": word, "dict": dict}
    return {"entries": entries, "word": word, "dict": dict}


@app.get("/api/random")
async def random_word(
    dict: str = Query("av-ru", pattern="^(av-ru|ru-av)$"),
):
    """Получить случайное слово (для 'слова дня')."""
    entry = dict_manager.get_random(dict_name=dict)
    if entry is None:
        return {"entry": None}
    return {"entry": entry}


@app.get("/api/stats")
async def stats():
    """Статистика словарей."""
    result = {}
    for name, d in dict_manager.dictionaries.items():
        result[name] = {
            "total_entries": len(d.entries),
            "unique_words": len(d.word_index),
        }
    return result


# Раздача статических файлов Mini App
if WEBAPP_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(WEBAPP_DIR)), name="webapp_assets")

    @app.get("/")
    async def serve_webapp():
        return FileResponse(str(WEBAPP_DIR / "index.html"))

    @app.get("/style.css")
    async def serve_css():
        return FileResponse(str(WEBAPP_DIR / "style.css"), media_type="text/css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(str(WEBAPP_DIR / "app.js"), media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
