"""
Модуль для работы с базой данных (SQLAlchemy + PostgreSQL).
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, select
from datetime import datetime

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# SQLAlchemy requires postgresql+asyncpg:// for async postgres connections
db_url = DATABASE_URL
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

try:
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
except Exception as e:
    logger.error(f"Ошибка подключения к БД: {e}")
    engine = None
    async_session = None


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Subscriber(Base):
    __tablename__ = "subscribers"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


async def init_db():
    """Создает таблицы в базе данных, если их нет."""
    if not engine:
        return
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных успешно инициализирована.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")


async def add_subscriber(chat_id: int) -> bool:
    """
    Добавляет подписчика.
    Возвращает True, если добавлен успешно, False если уже существует.
    """
    if not async_session:
        return False
        
    async with async_session() as session:
        # Проверяем, существует ли уже
        result = await session.execute(select(Subscriber).filter_by(chat_id=chat_id))
        if result.scalar_one_or_none():
            return False
            
        new_sub = Subscriber(chat_id=chat_id)
        session.add(new_sub)
        try:
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления подписчика: {e}")
            return False


async def remove_subscriber(chat_id: int) -> bool:
    """
    Удаляет подписчика.
    Возвращает True, если удален, False если его не было.
    """
    if not async_session:
        return False
        
    async with async_session() as session:
        result = await session.execute(select(Subscriber).filter_by(chat_id=chat_id))
        sub = result.scalar_one_or_none()
        if sub:
            await session.delete(sub)
            await session.commit()
            return True
        return False


async def get_all_subscribers() -> list[int]:
    """Возвращает список всех chat_id подписчиков."""
    if not async_session:
        return []
        
    async with async_session() as session:
        result = await session.execute(select(Subscriber.chat_id))
        return list(result.scalars().all())
