# Project State

> Updated: 2026-05-22 | Branch: feat/generator-agent-interview | Milestone: v0.1 — MVP

---

## Milestone progress — v0.1

| Feature | Spec | Impl | Tests |
| --- | :---: | :---: | :---: |
| Project scaffold | ✅ | ✅ | — |
| Core Pydantic models (`AgentSpec`, `AgentState`, `Message`, etc.) | — | ✅ | ✅ |
| Database layer (SQLModel + SQLite) | — | ✅ | ✅ |
| Generator Agent — interview | ✅ | ✅ | ✅ |
| Generator Agent — org generation | — | — | — |
| LLM router | — | ✅ (Anthropic only) | ✅ |
| LLM clients (Ollama, Anthropic, OpenAI, Google) | — | ✅ (Anthropic only) | ✅ |
| Async message dispatcher | — | — | — |
| Agent loop (asyncio, pause/resume, work hours) | — | — | — |
| Memory layer (Chroma — per-agent + global KB) | — | — | — |
| Deliverables output (`data/outputs/`) | — | — | — |
| FastAPI app + REST routes | — | — | — |
| WebSocket handler (real-time agent state) | — | — | — |
| Onboarding view (React) | — | — | — |
| 2D workspace (PixiJS) | — | — | — |
| Org chart view (React) | — | — | — |
| Blocking questions UI | — | — | — |
| Deliverables view (React) | — | — | — |

---

## Environment

| Step | Status |
| --- | :---: |
| `.env` created from `.env.example` | ✅ |
| `git init` + scaffold commit | ✅ |
| `uv sync` (backend deps) | ✅ |
| `pnpm install` (frontend deps) | ✅ |
| Ollama running + model pulled (`qwen3.5:9b`) | ✅ |

---

## Last session — 2026-05-20

- Ollama model pulled (`qwen3.5:9b`) — local inference ready
- Core Pydantic models implemented (TDD, 44 tests, ruff + mypy --strict clean):
  - `agents/models.py` — `AgentSpec`, `AgentState`, `AgentStatus` (`StrEnum`), `Skill`, `BlockingQuestion`
  - `messaging/models.py` — `Message`, `Conversation`
  - `memory/models.py` — `Memory`
  - `projects/models.py` — `Project`, `ProjectStatus` (`StrEnum`)
  - `deliverables/models.py` — `Deliverable`
- Database layer implemented (TDD, 80 tests total, ruff + mypy --strict clean):
  - `db/tables.py` — 9 SQLModel table classes (one per domain model)
  - `db/engine.py` — async engine (`aiosqlite`), `create_db_and_tables`, `get_session`
  - `db/convert.py` — 18 `to_table`/`from_table` functions; JSON + ISO 8601 serialization
  - `tests/conftest.py` — shared async in-memory fixture for DB tests
- ADR 0002 (séparation Pydantic/SQLModel), ADR 0003 (sessions async), ADR 0004 (BlockingQuestion) documentés
- `feat/core-pydantic-models` mergé dans main, branche locale supprimée

**Stopped at:** merge complete — ready for Generator Agent feature spec

---

## Last session — 2026-05-20 (continued)

- Feature spec written and validated: Generator Agent — interview
  - `docs/specs/2026-05-20-generator-agent-interview.md` — full Feature Brief
  - `docs/specs/2026-05-20-generator-agent-interview-roleplay.md` — annotated interview flow example
    (reference for writing the interview prompt)
- Key design decisions:
  - Interview = structured (12 mandatory items) + conversational (adaptive order)
  - End condition: `ready_to_generate: true` flag in the LLM JSON payload
  - Feature 1 output: SQLite transcript + structured `BusinessContext` Pydantic model
  - Skills: intent-level in Feature 1; details co-constructed per agent post-onboarding (dedicated future feature)
  - LLM routing: driven by configured API keys — no forced provider order, Ollama valid for fully local setups

**Stopped at:** Feature Brief validated — ready for implementation plan (Phase 2 of /feature)

---

## Last session — 2026-05-21

- Implementation plan written and saved: `docs/specs/2026-05-20-generator-agent-interview-plan.md`
- Full TDD implementation of Generator Agent — interview (T1–T7):
  - `generator/models.py` — `BusinessContext` Pydantic model
  - `db/tables.py` + `db/convert.py` — `BusinessContextTable` + convert functions
  - `prompts/loader.py` — `PromptLoader` (.md files, YAML frontmatter, `{variable}` rendering)
  - `llm/anthropic_client.py` — async `AnthropicClient` wrapper
  - `router/router.py` — minimal `LLMRouter` (Anthropic-only, reads `ANTHROPIC_API_KEY`)
  - `prompts/generator/interview.md` — real interview prompt (12 mandatory items, closing sequence)
  - `prompts/generator/extract_business_context.md` — extraction prompt (transcript → BusinessContext JSON)
  - `generator/interview.py` — `GeneratorInterview` orchestration (multi-turn, retry, persist, resume)
  - `scripts/smoke_generator_interview.py` — end-to-end smoke test (real API, in-memory SQLite)
- 128 tests passing, ruff + mypy --strict clean
- Smoke test validated: `BusinessContext` correctly produced for Alex Chen / Luminescence scenario
- Code review (subagent) identified 1 blocking + 4 warnings + 1 spec gap → all fixed:
  - `ValidationError` from LLM extraction now wrapped in `InterviewError`
  - `_completed` flag prevents duplicate `BusinessContext` on repeated `reply()` calls
  - `LLMRouter` no longer stores the raw API key in memory
  - Kickoff string moved from Python source to `interview.md` frontmatter
  - `assert` guards replaced with explicit `InterviewError` raises
  - `existing_tools` added as 12th mandatory item
- 130 tests passing after fixes

**Stopped at:** code review fixes committed — ready for merge to main

---

## Next steps

1. **Merge** `feat/generator-agent-interview` into `main`, delete local branch
2. **Next feature** — Generator Agent — org generation: consume `BusinessContext` to generate `AgentSpec` hierarchy

---

## Technical debt

- `eslint.config.js`: written against ESLint 9 API — may need adjustments for ESLint 10 after `pnpm install`
- `vite.config.ts`: written against Vite 6 API — to validate against installed Vite 8
- `resume()` in `GeneratorInterview`: N sequential SELECTs (one per message) — acceptable
  for v0.1 short conversations, replace with `WHERE id IN (...)` if conversations grow

---

## Decisions log

Full ADRs in `docs/decisions/`. Summary:

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-05-18 | No AI framework (LangChain, LangGraph, etc.) | Custom loop + message bus; official SDKs only |
| 2026-05-18 | PixiJS from v0.1 | Avoids full rewrite when adding animations in v0.3 |
| 2026-05-18 | WebSockets for real-time | Bidirectional needed; SSE is unidirectional |
| 2026-05-18 | asyncio tasks for scheduler | APScheduler/Celery overkill for local single-user app |
| 2026-05-18 | Generator Agent ≠ COO | Different lifecycle and LLM quality requirements |
| 2026-05-18 | Hierarchy depth = `int`, no cap | Complex businesses may need N-3 or deeper |
| 2026-05-18 | MCP for integrations (to validate at v0.2 start) | Reuse open ecosystem rather than custom connectors |
| 2026-05-18 | Projects feature deferred to v0.2 | v0.1 focuses on core autonomous loop |
| 2026-05-20 | Pydantic domain models ≠ SQLModel tables (ADR 0002) | Persistence concerns isolated in `db/`; FastAPI contract stays clean |
| 2026-05-20 | Async SQLite sessions via aiosqlite (ADR 0003) | asyncio-first app; sync sessions would block the event loop |
| 2026-05-20 | BlockingQuestion as first-class persisted entity (ADR 0004) | Schema complet dès le début; shape connue via le protocole WebSocket |
