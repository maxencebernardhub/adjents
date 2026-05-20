# ADR 0003 — Async SQLite sessions via aiosqlite

**Date**: 2026-05-20
**Status**: Accepted

---

## Context

The backend is asyncio-first: FastAPI routes, WebSocket handlers, and agent loops all
run as asyncio coroutines. SQLModel — our chosen ORM — is built on SQLAlchemy and
supports two session modes: synchronous (`Session`) and asynchronous (`AsyncSession`).

The database is SQLite, accessed via the `sqlite:///` driver by default.
`aiosqlite` is a thin async wrapper around Python's built-in `sqlite3` module that
enables non-blocking SQLite access from asyncio coroutines.

---

## Decision

We use **async SQLite sessions** throughout the backend:

- Engine: `create_async_engine("sqlite+aiosqlite:///./data/adjents.db")`
- Session: `sqlmodel.ext.asyncio.session.AsyncSession`
- All DB calls use `await session.exec(...)`, `await session.commit()`, etc.
- `aiosqlite` is added as a runtime dependency in `pyproject.toml`

---

## Rationale

**Why not synchronous sessions**:

1. **Event loop blocking**: a synchronous I/O call inside an asyncio coroutine blocks
   the entire event loop. Every agent loop iteration reads `AgentSpec` and `AgentState`
   from SQLite and writes back after each action. With N agents running in parallel,
   synchronous DB calls would serialize all coroutines through each DB operation —
   effectively making the multi-agent loop single-threaded at the I/O level.

2. **WebSocket latency**: agent state updates trigger WebSocket broadcasts. If DB writes
   block the event loop, WebSocket messages are delayed for the duration of every
   DB call across every running agent. For a real-time workspace UI, this is
   unacceptable regardless of how fast each individual SQLite call is.

3. **Architectural incoherence**: combining an asyncio-first framework with synchronous
   I/O requires workarounds (`asyncio.to_thread()`) at every call site. This adds
   boilerplate, obscures the data flow, and signals a mismatch between the intended
   and actual architecture.

4. **Migration path**: if the database ever moves from SQLite to PostgreSQL, the
   async driver (`asyncpg`) integrates identically with `AsyncSession`. A sync
   codebase would require a full session-layer rewrite at migration time.

**Why `aiosqlite`**:

`aiosqlite` is the only production-grade async adapter for SQLite with asyncio. It
wraps `sqlite3` in a background thread and exposes an `await`-compatible API — the
standard approach for making SQLite non-blocking in asyncio applications. The library
is stable (~900 lines, no transitive dependencies), actively maintained, and the
default choice in every major asyncio + SQLite guide.

---

## Consequences

- `aiosqlite` added to `[project.dependencies]` in `pyproject.toml`
- `backend/adjents/db/engine.py` uses `create_async_engine` and `AsyncSession`
- All repository functions are `async def` and use `await session.exec(...)`
- FastAPI dependency injection yields `AsyncSession` via `async def get_session()`
- Tests use `pytest-asyncio` (already in dev dependencies) with an in-memory async
  engine: `create_async_engine("sqlite+aiosqlite:///:memory:")`

---

## Alternatives considered

**Sync sessions + `asyncio.to_thread()`**: wrap each DB call in a thread pool executor
to avoid blocking the event loop. Works in theory, but requires wrappers at every call
site and makes the data flow harder to follow. Rejected: trades architectural clarity
for marginal implementation simplicity.

**Sync sessions directly**: acceptable only for scripts or CLI tools, not for an
asyncio server with concurrent agent loops. Rejected outright.
