# Adjents

> Describe your business. Get your AI workforce.

Adjents is an open-source AI agent platform that generates a full team of autonomous
AI agents for solopreneurs — from a single onboarding conversation. No templates,
no graph builders, no YAML. Just talk.

A dedicated **Generator Agent** interviews you about your business, then creates a
complete organization: a COO, domain leads (Sales, Finance, Marketing, Ops...), and
specialists below them. Each agent has its own memory, skills, and the autonomy to
act without being told what to do at every step.

> **Status**: Pre-MVP — v0.1 in active development.
> See [VISION.md](docs/VISION.md) for the full product specification.

---

## What v0.1 includes

- **Conversational onboarding** — Generator Agent conducts a deep interview and
  produces a full persistent agent organization tailored to your business
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
  Gemini) are optional enhancements for complex tasks

---

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)
- [Ollama](https://ollama.com/) with at least one model pulled (e.g. `ollama pull qwen2.5:7b`)
- Optional: Anthropic / OpenAI / Google API key for cloud LLM tasks

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
# Start backend (FastAPI :8000) + frontend (Vite :5173)
make dev

# Run tests
make test

# Lint and type-check
make lint
make typecheck
```

Then open [http://localhost:5173](http://localhost:5173).

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

- **Agents are data, not code** — `AgentSpec` (Pydantic) + prompt file + memory namespace
- **No AI framework** — official LLM SDKs + custom agent loop + message bus from scratch
- **Local-first** — SQLite + Chroma, works offline, cloud is optional
- **PixiJS** for the 2D workspace canvas, React for everything else

---

## Roadmap

| Version | Scope |
| --- | --- |
| **v0.1** | Onboarding, autonomous agent loop, 2D workspace, deliverables *(in progress)* |
| **v0.2** | Python sandbox for skills, web search, external event triggers, projects |
| **v0.3** | MCP integrations, animated UI sprites |
| **v1.0** | One-click deploy for non-technical users |

See [VISION.md §4](docs/VISION.md) for the detailed roadmap and integration philosophy.

---

## Contributing

This project is in early development. Contributions, issues, and feedback are welcome.

Architecture decisions are documented in [docs/decisions/](docs/decisions/) as ADRs.
Please open an issue before submitting a significant pull request.

## License

[MIT](LICENSE) — Maxence Bernard, 2026
