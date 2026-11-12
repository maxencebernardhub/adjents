"""Tests for db.engine: database URL, engine and session factories, table creation."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlmodel.ext.asyncio.session import AsyncSession

from adjents.db import engine as engine_module
from adjents.db.engine import (
    _async_url,
    create_db_and_tables,
    get_session,
    make_engine,
    make_session_factory,
)
from adjents.db.tables import SkillTable

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO_ROOT / "data" / "adjents.db"


def _run_python(code: str, **env: str) -> subprocess.CompletedProcess[str]:
    """Run `code` in a fresh interpreter, so no module is imported beforehand."""
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=False,
    )


async def _table_names(conn: AsyncConnection) -> set[str]:
    return set(await conn.run_sync(lambda sync: inspect(sync).get_table_names()))


# --- _async_url ---


@pytest.mark.parametrize(
    ("raw", "database"),
    [
        ("sqlite:///./data/a.db", "./data/a.db"),
        ("sqlite:////abs/a.db", "/abs/a.db"),
        ("sqlite://", None),
        ("sqlite:///./aiosqlite-data/a.db", "./aiosqlite-data/a.db"),
    ],
)
def test_async_url_rewrites_plain_sqlite_to_aiosqlite(
    raw: str, database: str | None
) -> None:
    url = _async_url(raw)
    assert url.drivername == "sqlite+aiosqlite"
    assert url.database == database


@pytest.mark.parametrize(
    "raw", ["sqlite+aiosqlite:///x.db", "postgresql+asyncpg://u:secret@h/db"]
)
def test_async_url_keeps_async_urls(raw: str) -> None:
    url = _async_url(raw)
    assert url.render_as_string(hide_password=False) == raw


# --- make_engine ---


async def test_make_engine_default_path_is_anchored_on_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Not relative to the working directory: `make dev` runs from `backend/`."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    engine = make_engine()
    assert engine.url.drivername == "sqlite+aiosqlite"
    assert engine.url.database == str(_DEFAULT_DB)
    await engine.dispose()


async def test_make_engine_empty_database_url_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    engine = make_engine()
    assert engine.url.database == str(_DEFAULT_DB)
    await engine.dispose()


async def test_make_engine_reads_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'env.db'}")
    engine = make_engine()
    assert engine.url.drivername == "sqlite+aiosqlite"
    assert engine.url.database == str(tmp_path / "env.db")
    await engine.dispose()


async def test_make_engine_explicit_url_takes_priority_over_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./from-env.db")
    engine = make_engine("sqlite://")
    assert engine.url.drivername == "sqlite+aiosqlite"
    assert engine.url.database is None
    await engine.dispose()


def test_module_creates_no_engine_at_import() -> None:
    """An empty DATABASE_URL used to make the import itself fail."""
    result = _run_python("import adjents.db.engine", DATABASE_URL="")
    assert result.returncode == 0, result.stderr
    assert not hasattr(engine_module, "engine")


# --- create_db_and_tables ---


def test_create_db_and_tables_registers_tables_by_itself() -> None:
    """Callers no longer need to import `adjents.db.tables` first."""
    code = (
        "import asyncio\n"
        "from sqlalchemy import inspect\n"
        "from adjents.db.engine import create_db_and_tables, make_engine\n"
        "async def main():\n"
        "    engine = make_engine('sqlite+aiosqlite://')\n"
        "    await create_db_and_tables(engine)\n"
        "    async with engine.connect() as conn:\n"
        "        names = await conn.run_sync(\n"
        "            lambda c: inspect(c).get_table_names()\n"
        "        )\n"
        "    await engine.dispose()\n"
        "    print(len(names))\n"
        "asyncio.run(main())\n"
    )
    result = _run_python(code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "12"


async def test_create_db_and_tables_creates_missing_parent_directories(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "sub" / "dir" / "a.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_file}")
    await create_db_and_tables(engine)
    async with engine.connect() as conn:
        assert "skills" in await _table_names(conn)
    await engine.dispose()
    assert db_file.is_file()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite+aiosqlite://",
        "sqlite+aiosqlite:///:memory:",
        # SQLAlchemy warns that it will stop picking StaticPool from `mode=memory`;
        # the pool is irrelevant here, only the directory handling is tested.
        pytest.param(
            "sqlite+aiosqlite:///file:mem1?mode=memory&cache=shared&uri=true",
            marks=pytest.mark.filterwarnings(
                "ignore::sqlalchemy.exc.SADeprecationWarning"
            ),
        ),
    ],
)
async def test_create_db_and_tables_creates_no_directory_for_in_memory_urls(
    url: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    engine = make_engine(url)
    await create_db_and_tables(engine)
    await engine.dispose()
    assert list(tmp_path.iterdir()) == []


# --- make_session_factory / get_session ---


async def test_session_factory_keeps_attributes_readable_after_commit() -> None:
    """With expire_on_commit=True, this read raised MissingGreenlet in async code."""
    engine = make_engine("sqlite+aiosqlite://")
    await create_db_and_tables(engine)
    factory = make_session_factory(engine)
    async with factory() as session:
        row = SkillTable(
            id="skill-001",
            name="Draft invoice",
            description="Generates an invoice.",
            inputs="[]",
            outputs="[]",
            requires_human_review=False,
        )
        session.add(row)
        await session.commit()
        assert row.name == "Draft invoice"
    await engine.dispose()


async def test_get_session_yields_a_session_bound_to_the_factory_engine() -> None:
    engine = make_engine("sqlite+aiosqlite://")
    sessions = get_session(make_session_factory(engine))
    session = await anext(sessions)
    assert isinstance(session, AsyncSession)
    assert session.bind is engine
    await sessions.aclose()
    await engine.dispose()
