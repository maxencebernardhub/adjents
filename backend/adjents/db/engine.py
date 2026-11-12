"""Async SQLite engine and session factories (ADR 0003).

The engine uses the `sqlite+aiosqlite` driver, so database calls never block the
event loop shared by agent loops, API routes and WebSocket handlers. aiosqlite runs
`sqlite3` in a background thread: it does not make queries faster, it lets other
coroutines run while one waits.

Nothing is created at import time: callers build an engine with `make_engine()` and
a session factory with `make_session_factory()`, then pass them on. The database URL
is, in order: the `url` argument, the `DATABASE_URL` variable of the process
environment (an empty value counts as unset), or the default file
`<repository root>/data/adjents.db` (ARCHITECTURE §1). The default is an absolute
path computed from this file's location, so it does not depend on the working
directory; it assumes the code runs from the source tree, as `uv sync` installs it.
A relative path given in a URL stays relative to the working directory, as in
SQLAlchemy. A plain `sqlite` URL is rewritten to the `sqlite+aiosqlite` driver.

Importing this module imports `adjents.db.tables`, which registers every table in
`SQLModel.metadata`: `create_db_and_tables()` therefore always knows all of them.

Place in the flow: no application code calls this module yet. It is meant for the
FastAPI app — `make_engine()`, `create_db_and_tables()` and `make_session_factory()`
at startup (lifespan), `get_session()` as the session dependency of routes. The
orchestrators receive their `AsyncSession` from their caller.

Entry points: `make_engine()`, `make_session_factory()`, `create_db_and_tables()`,
`get_session()`.

Related ADRs: 0002 (domain models vs tables), 0003 (async SQLite sessions).
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import adjents.db.tables  # noqa: F401  # registers every table in SQLModel.metadata

# backend/adjents/db/engine.py → parents[3] is the repository root.
_DEFAULT_DB_FILE = Path(__file__).resolve().parents[3] / "data" / "adjents.db"


def _async_url(raw: str) -> URL:
    """Parse `raw`, rewriting the plain `sqlite` driver to `sqlite+aiosqlite`.

    Any other driver, including `sqlite+aiosqlite`, is kept unchanged. A `URL` is
    returned rather than a string: rendering one as text masks its password.
    """
    url = make_url(raw)
    if url.drivername == "sqlite":
        return url.set(drivername="sqlite+aiosqlite")
    return url


def make_engine(url: str | None = None) -> AsyncEngine:
    """Build an async engine; no connection is opened until it is first used.

    Args:
        url: Database URL. None falls back to `DATABASE_URL`, then to the default
            file (see the module docstring).

    Returns:
        A new engine; the caller disposes of it (`await engine.dispose()`).

    Raises:
        sqlalchemy.exc.ArgumentError: The URL cannot be parsed.
    """
    raw = url or os.getenv("DATABASE_URL") or f"sqlite+aiosqlite:///{_DEFAULT_DB_FILE}"
    return create_async_engine(_async_url(raw))


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build a factory of `AsyncSession`s bound to `engine`.

    Sessions keep loaded objects readable after a commit (`expire_on_commit=False`).
    With SQLAlchemy's default, a commit expires them, and reading an attribute then
    raises `MissingGreenlet`: the implicit reload cannot run in async code. The
    flip side: after a commit, `session.get()` returns the object already in the
    session without querying the database.

    Args:
        engine: Engine the sessions use.

    Returns:
        The session factory; `async with factory() as session:` opens one.
    """
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables(engine: AsyncEngine) -> None:
    """Create every table that does not exist yet, and the database's directory.

    `create_all` only creates missing tables; it never alters an existing one.
    SQLite does not create missing parent directories of a database file, so they
    are created here — except for in-memory databases (no database name,
    `:memory:`, or a `file:` URI).

    Args:
        engine: Engine of the database to initialize.
    """
    _create_parent_directory(engine.url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Yield a session from `factory`, closed when the caller is done with it.

    Args:
        factory: Session factory from `make_session_factory()`.

    Yields:
        A new session.
    """
    async with factory() as session:
        yield session


def _create_parent_directory(url: URL) -> None:
    """Create the parent directories of a SQLite database file, if any."""
    if url.get_backend_name() != "sqlite":
        return
    database = url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)
