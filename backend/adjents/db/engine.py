"""Async SQLite engine and session lifecycle (ADR 0003).

The engine uses sqlite+aiosqlite so all DB calls are non-blocking in asyncio
coroutines. DATABASE_URL from the environment is normalised to the async driver
if needed; tests override it by creating their own engine directly.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


def _async_url(raw: str) -> str:
    if raw.startswith("sqlite:///") and "aiosqlite" not in raw:
        return raw.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return raw


engine: AsyncEngine = create_async_engine(
    _async_url(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/adjents.db")),
    echo=False,
)


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session
