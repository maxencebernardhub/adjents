"""Async SQLite engine and session lifecycle (ADR 0003).

The engine uses the `sqlite+aiosqlite` driver, so database calls never block the
event loop shared by agent loops, API routes and WebSocket handlers. aiosqlite runs
`sqlite3` in a background thread: it does not make queries faster, it lets other
coroutines run while one waits.

The module-level `engine` is created at import time from the `DATABASE_URL`
environment variable, read from the process environment when the module is first
imported. The default, `sqlite+aiosqlite:///./data/adjents.db`, is a path relative
to the current working directory. A plain `sqlite:///` URL is rewritten to the
async driver.

Place in the flow: no code imports this module yet. It is meant for the FastAPI app
— `create_db_and_tables()` at startup (lifespan), `get_session()` as the session
dependency of routes. Tests do not use it: `tests/conftest.py` builds its own
in-memory engine per test, and the orchestrators receive their `AsyncSession` from
their caller.

Entry points: `engine`, `create_db_and_tables()`, `get_session()`.

Related ADRs: 0002 (domain models vs tables), 0003 (async SQLite sessions).
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


def _async_url(raw: str) -> str:
    """Return `raw` with a `sqlite:///` scheme rewritten to `sqlite+aiosqlite:///`.

    URLs that already name aiosqlite, and non-SQLite URLs, are returned unchanged.
    """
    if raw.startswith("sqlite:///") and "aiosqlite" not in raw:
        return raw.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return raw


engine: AsyncEngine = create_async_engine(
    _async_url(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/adjents.db")),
    echo=False,
)


async def create_db_and_tables() -> None:
    """Create every table registered in `SQLModel.metadata` that does not exist yet.

    `create_all` only creates missing tables; it never alters an existing one.
    Tables are registered by importing `adjents.db.tables`, which this module does
    not import: the caller must have imported it, or no table is created. SQLite
    does not create missing parent directories of the database file.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield an `AsyncSession` bound to `engine`, closed when the caller is done.

    The session keeps SQLAlchemy's defaults, including `expire_on_commit=True`:
    after a commit, loaded objects are expired, and reading one of their attributes
    raises `MissingGreenlet` (an implicit reload cannot run in async code) unless
    the object is refreshed first with `await session.refresh(obj)`.

    Yields:
        A new session.
    """
    async with AsyncSession(engine) as session:
        yield session
