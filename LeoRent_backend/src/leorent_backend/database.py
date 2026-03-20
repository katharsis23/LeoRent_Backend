from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)
from src.leorent_backend.config.database import DATABASE_CONFIG
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

# Declarative base
BASE = declarative_base()


# Async engine
engine = create_async_engine(
    DATABASE_CONFIG.database_url.get_secret_value(),
    echo=True,
    pool_pre_ping=True,
)


# Async session
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Async session context manager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# Test connection
async def test_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        logger.info("Connection successful")
    except SQLAlchemyError as e:
        logger.error(f"Connection failed: {e}")
