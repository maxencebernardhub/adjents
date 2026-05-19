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
