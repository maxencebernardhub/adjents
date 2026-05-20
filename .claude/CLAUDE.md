# Adjents

PROJECT_TYPE: development

AI agent platform that generates a full team of AI agents for solopreneurs from a
single onboarding conversation. No templates, no graph builders, no YAML.

Full vision: @./docs/VISION.md — Architecture: @./docs/ARCHITECTURE.md — State: @./PROJECT_STATE.md

## Status

Pre-MVP. Building v0.1: onboarding flow + autonomous agent loop + 2D RPG workspace.
Single user, local-first. No real-world execution in v0.1.

## Tech stack

- **Backend**: Python 3.13+, FastAPI, Pydantic v2, SQLModel, asyncio-first
- **Frontend**: TypeScript, React 19, Vite, Tailwind CSS, shadcn/ui, PixiJS (@pixi/react)
- **State**: Zustand (client), TanStack Query (server), WebSockets (real-time)
- **Storage**: SQLite via SQLModel + Chroma (vector memory)
- **LLM local**: Ollama (any model the user has pulled)
- **LLM cloud**: Anthropic Claude, OpenAI, Google Gemini (frontier tasks only)
- **Package managers**: `uv` (Python), `pnpm` (JS)

## Key commands

```bash
make install    # uv sync + pnpm install
make dev        # FastAPI :8000 + Vite :5173
make test       # pytest + vitest
make lint       # ruff + mypy + eslint + prettier
make typecheck  # mypy --strict + tsc --noEmit
```

## Architecture rules (non-negotiable)

1. **Agents are data, not code.** Agent = AgentSpec (Pydantic) + prompt file + memory
   namespace + skill list. Never subclass per agent.
2. **All agent communication is async typed message-passing** via the MessageDispatcher.
   Never direct method calls between agents.
3. **Memory = per-agent (namespaced Chroma collection) + global KB (shared collection).**
4. **The LLMRouter decides every model choice.** No agent picks its own model.
   sensitivity=high → local only. Generator Agent → always cloud.
5. **Local-first.** Must work 100% offline with Ollama. Cloud is an enhancement.
6. **No AI framework.** Use official LLM SDKs (anthropic, openai, google-generativeai),
   chromadb, and sqlmodel. The agent loop, bus, and router are written from scratch.
7. **Agent loop = asyncio task per agent.** Pause/resume via is_paused flag in SQLite.
   Work hours via work_hours field. No APScheduler, no Celery.

## What NOT to do

- No real-world execution in v0.1 (no emails, no external API calls, no file writes
  outside `./data/`). That is v0.2 scope.
- No LangChain, LangGraph, LlamaIndex, CrewAI, or AutoGen. See ARCHITECTURE.md §2.
- No prompt strings in Python source. Prompts live in `backend/adjents/prompts/*.md`.
- No `any` in TypeScript. No Python subclass per agent. No >300-line files.
- No feature without a test. No dependency added without an explicit request.

## Conventions

- Type-hint everything. `mypy --strict` must pass at all times.
- `async def` by default for I/O. Sync only for pure CPU work.
- Prompts: `backend/adjents/prompts/<agent_type>/<purpose>.md`, loaded via PromptLoader.
- ADRs: `docs/decisions/NNNN-title.md`. Never delete — mark Deprecated or Superseded.
- Feature specs: `docs/specs/YYYY-MM-DD-feature-name.md`.

## Git workflow

- Branches: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`
- Commits: conventional (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`)
- Always run `make lint && make test` before committing.

## Working rules

- Read the full target file before editing it.
- Prefer targeted edits over broad refactors. One file changed if one file suffices.
- Do not rename or move files without an explicit reason.
- Use `uv run <cmd>` to invoke Python tools (pytest, ruff, mypy). Never call `.venv/bin/` directly.
- Update `PROJECT_STATE.md` at the end of every completed feature or significant task.
- When unsure on a load-bearing decision not covered in VISION.md or ARCHITECTURE.md,
  ask before implementing.

## Security

- Never read, modify, or commit `.env` or any file containing secrets.
- Ask before changing the global project structure.
- Flag ambiguity about expected behavior before acting.
