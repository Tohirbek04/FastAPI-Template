.PHONY: db dev migrate makemigration seed test lint format worker scheduler

db:
	docker compose -f docker-compose.dev.yml up -d

dev:
	uv run uvicorn app.main:app --reload

migrate:
	uv run alembic upgrade head

makemigration:
	uv run alembic revision --autogenerate -m "$(m)"

seed:
	uv run python scripts/seed.py

test:
	uv run pytest -v

lint:
	uv run ruff check . && uv run ruff format --check . && uv run mypy

format:
	uv run ruff check --fix . && uv run ruff format .

worker:
	uv run taskiq worker app.tasks.broker:broker

scheduler:
	uv run taskiq scheduler app.tasks.scheduler:scheduler
