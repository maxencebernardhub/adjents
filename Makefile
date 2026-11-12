.PHONY: install dev test lint typecheck

install:
	cd backend && uv sync --all-groups
	cd frontend && pnpm install
	mkdir -p data/outputs data/chroma

dev:
	@trap 'kill %1 %2 2>/dev/null; exit' INT TERM; \
	(cd backend && uv run uvicorn adjents.api.main:app --reload --port 8000) & \
	(cd frontend && pnpm dev) & \
	wait

test:
	cd backend && uv run pytest
	cd frontend && pnpm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint && pnpm format:check

typecheck:
	cd backend && uv run mypy --strict adjents/ tests/
	cd frontend && pnpm typecheck
