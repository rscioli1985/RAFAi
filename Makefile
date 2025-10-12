SHELL := /bin/bash

.PHONY: up down logs migrate app ingest-dry-run fmt lint type

up:
	cd infra && docker compose up -d

down:
	cd infra && docker compose down

logs:
	cd infra && docker compose logs -f

migrate:
	alembic upgrade head

app:
	python -m services.backend

ingest-dry-run:
	python -m services.ingestion.cli run-daily --dry-run

fmt:
	ruff check --select I --fix . || true
	black .

lint:
	ruff check .

type:
	mypy services || true

