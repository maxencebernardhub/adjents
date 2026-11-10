# Adjents

> Describe your business. Get your AI workforce.

Adjents is an open-source AI agent platform that generates a full team of autonomous
AI agents for solopreneurs — from a single onboarding conversation. No templates,
no graph builders, no YAML. Just talk.

A dedicated **Generator Agent** interviews you about your business, then creates a
complete organization: a COO, domain leads (Sales, Finance, Marketing, Ops...), and
specialists below them. Each agent has its own memory, skills, and the autonomy to
act without being told what to do at every step.

> **Status**: Pre-MVP — v0.1 in active development. The backend core works today and
> runs through smoke scripts; the web app (API, workspace, chat) is not built yet.
> See [VISION.md](docs/VISION.md) for the full product specification.

---

## v0.1 scope

### Working today (backend)

- **Conversational onboarding** — Generator Agent conducts a deep interview and
  produces a full persistent agent organization tailored to your business
- **Post-generation team setup** — before agents go live, the user meets each agent
  one-on-one; each agent presents itself and can be adjusted; changes are applied at
  validation time via a single LLM extraction call
- **Direct agent reconfiguration** — after go-live, open a conversation with any agent
  to rename it, update its responsibilities, adjust skills, or change work hours;
  structural changes (domain, hierarchy) are deferred to v0.2

### In progress

- **Autonomous agent loop** — agents wake up on a configurable schedule, reason
  about their objectives, and act without waiting for instructions
- **2D RPG workspace** — a house-style interface where each agent is a named
  character with a visual state (idle, working, in a meeting...)
- **Multi-agent chat** — talk to any agent directly; agents call each other to
  collaborate or delegate
- **Blocking questions** — agents surface decisions that require human judgement
  in a dedicated notification zone
- **Deliverables** — agents write outputs (documents, drafts, notes) to a local
  structured directory
- **Local-first** — runs 100% offline with Ollama; cloud LLMs (Claude, OpenAI,
  Gemini) are optional enhancements for complex tasks. Today only the Anthropic
  client exists; Ollama, OpenAI and Gemini arrive with the LLM router

---

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 24 and [pnpm](https://pnpm.io/) (the pinned pnpm version is selected
  automatically from `frontend/package.json`)
- An Anthropic API key — required by the features working today
- [Ollama](https://ollama.com/) with at least one model pulled
  (e.g. `ollama pull qwen3.5:4b`) — used once the LLM router lands
- Optional: OpenAI / Google API key (once the LLM router lands)

## Installation

```bash
git clone https://github.com/maxencebernardhub/adjents.git
cd adjents

# Copy and fill in environment variables
cp .env.example .env

# Install all dependencies (backend + frontend)
make install
```

## Usage

```bash
# Run tests
make test

# Lint and type-check
make lint
make typecheck
```

To see the working features end to end, run the smoke scripts (real LLM calls,
`ANTHROPIC_API_KEY` required, except the default mock mode of the team setup script)
— see [backend/README.md](backend/README.md#scripts):

```bash
cd backend
uv run python scripts/smoke_generator_interview.py
uv run python scripts/smoke_generator_org.py
uv run python scripts/smoke_team_setup.py          # mock mode, no API key
uv run python scripts/smoke_team_setup.py --real
```

`make dev` (FastAPI on :8000 + Vite on :5173) becomes usable once the FastAPI app is
built.

---

## Project structure

```text
adjents/
├── backend/
│   ├── adjents/
│   │   ├── agents/        # AgentSpec, lifecycle, autonomous loop
│   │   ├── api/           # FastAPI routes + WebSocket handlers
│   │   ├── db/            # SQLite persistence (SQLModel + aiosqlite)
│   │   ├── deliverables/  # Deliverable writing and storage
│   │   ├── generator/     # Generator Agent: interview + org generation
│   │   ├── llm/           # LLM client abstractions
│   │   ├── memory/        # Per-agent Chroma store + global knowledge base
│   │   ├── messaging/     # Async typed message bus
│   │   ├── projects/      # Project and task management (v0.2)
│   │   ├── prompts/       # All prompts as .md files (agent/, coo/, generator/)
│   │   ├── router/        # LLM routing (local vs cloud)
│   │   └── scheduler/     # asyncio task runner + pause/resume
│   ├── scripts/           # Manual smoke tests (require API keys, not run by CI)
│   └── tests/             # pytest test suite
├── frontend/
│   ├── src/
│   │   ├── api/           # REST + WebSocket client
│   │   ├── components/    # Shared React components
│   │   ├── state/         # Zustand stores
│   │   ├── views/         # Onboarding, Workspace, OrgChart, Deliverables
│   │   └── workspace/     # PixiJS 2D house + agent sprites
│   └── tests/             # Vitest test suite
├── data/outputs/          # Agent-produced deliverables
├── docs/
│   ├── decisions/         # Architecture Decision Records (ADRs)
│   ├── specs/             # Feature specs and implementation plans
│   ├── ARCHITECTURE.md
│   └── VISION.md          # Full product vision and MVP scope
└── .github/
    └── workflows/         # CI/CD pipelines
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture reference,
including data models, agent loop design, WebSocket protocol, LLM routing rules, and
frontend technology choices.

Key decisions at a glance:

- **Agents are data, not code** — `AgentSpec` (Pydantic) + shared prompt templates +
  memory namespace
- **No AI framework** — official LLM SDKs + custom agent loop + message bus from scratch
- **Local-first** — SQLite + Chroma, works offline, cloud is optional
- **PixiJS** for the 2D workspace canvas, React for everything else

## Engineering practices

- Every significant decision is recorded as an ADR in [docs/decisions/](docs/decisions/)
- Each feature goes through a written spec and implementation plan
  ([docs/specs/](docs/specs/)), test-driven development, then a spec compliance review
  and a code review ([docs/reviews/](docs/reviews/))
- `mypy --strict`, Ruff, pytest, ESLint, Prettier and `tsc` on every push and pull
  request (GitHub Actions)

---

## Roadmap

| Version | Scope |
| --- | --- |
| **v0.1** | Onboarding, autonomous agent loop, 2D workspace, deliverables *(in progress)* |
| **v0.2** | Python sandbox for skills, web search, external event triggers, projects, org restructuring, first integrations |
| **v0.3** | Broader MCP integrations, animated UI sprites |
| **v1.0** | Production-ready, one-click deploy for non-technical users |

The roadmap is indicative. See [VISION.md §4](docs/VISION.md) for details and the
integration philosophy.

---

## Contributing

This project is in early development. Issues, feedback and discussions are welcome.

External pull requests are not accepted for now: the project has a single author,
which keeps its licensing open for future versions (see
[ADR 0013](docs/decisions/0013-mit-license-for-public-release.md)). If you have a
fix or an idea, please open an issue.

## License

The source code is released under the [MIT License](LICENSE) — Maxence Bernard, 2026.

The Adjents name, logo and the adjents.com domain are not covered by the license:
forks may reuse the code but must not present themselves as Adjents.
