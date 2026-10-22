# Adjents — Backend

FastAPI + SQLModel backend for the Adjents agent platform.

See the [main README](../README.md) and [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for full documentation.

## Development

```bash
uv sync --all-groups
uv run uvicorn adjents.api.main:app --reload --port 8000
```

## Tests

```bash
uv run pytest
```

## Lint & type-check

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict adjents/
```

## Scripts

One-off scripts to validate features against real APIs. Not run by pytest —
require API keys and are excluded from CI. Real-API runs make **paid** calls; the
models are chosen by `LLMRouter` (`router/router.py`) and printed at startup.

```bash
# Smoke test: Generator Agent interview (requires ANTHROPIC_API_KEY)
uv run python scripts/smoke_generator_interview.py

# Smoke test: Generator Agent org generation (requires ANTHROPIC_API_KEY)
uv run python scripts/smoke_generator_org.py

# Smoke test: Post-generation team setup + direct agent reconfiguration
# Mock mode (default): automated, no API key required
uv run python scripts/smoke_team_setup.py
# Real mode: live LLM calls, prints conversation to stdout
uv run python scripts/smoke_team_setup.py --real
```

Add `--llm-debug` to any real-API run to print, for each LLM call, its
`stop_reason`, output tokens and thinking summary (useful to calibrate
`max_tokens` and understand the model's choices). Thinking summaries contain the
scenario's business data. Shared helpers live in `scripts/_common.py`.
