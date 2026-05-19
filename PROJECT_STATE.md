# Project State

> Updated: 2026-05-19 | Branch: main | Milestone: v0.1 — MVP (setup)

---

## Milestone progress — v0.1

| Feature | Spec | Impl | Tests |
| --- | :---: | :---: | :---: |
| Project scaffold | ✅ | ✅ | — |
| Core Pydantic models (`AgentSpec`, `AgentState`, `Message`, etc.) | — | — | — |
| Database layer (SQLModel + SQLite) | — | — | — |
| Generator Agent — interview | — | — | — |
| Generator Agent — org generation | — | — | — |
| LLM router | — | — | — |
| LLM clients (Ollama, Anthropic, OpenAI, Google) | — | — | — |
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
| Ollama running + model pulled | — |

---

## Last session — 2026-05-19

- Defined full product vision (`docs/VISION.md`) and architecture (`docs/ARCHITECTURE.md`)
- Created complete project scaffold: backend Python structure, frontend React/TS structure, Makefile, `pyproject.toml`, `package.json`, prompt placeholders
- All dependencies set to latest stable versions (Python + JS)
- `make install` completed: 100 Python packages (uv), 219 JS packages (pnpm 11.1.3)
- VS Code Python interpreter pointed to `backend/.venv/bin/python` (Python 3.13.13)

**Stopped at:** lockfiles commit + ready to start first feature

---

## Next steps

1. **Pull Ollama model** — `ollama pull qwen3.5:9b` (required for local inference)
2. **Core Pydantic models** — `AgentSpec`, `AgentState`, `Message`, `Skill`, `Memory`, `Conversation`, `Deliverable`
3. **Database layer** — SQLModel table definitions + engine setup
4. **First feature spec** — run `/feature` for the Generator Agent onboarding interview

---

## Technical debt

- `eslint.config.js`: written against ESLint 9 API — may need adjustments for ESLint 10 after `pnpm install`
- `vite.config.ts`: written against Vite 6 API — to validate against installed Vite 8
- All prompt files are placeholders (`<!-- TODO: implement -->`) — need real content before any LLM call

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
