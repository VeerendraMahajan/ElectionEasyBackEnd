.PHONY: help install run test lint migrate sample docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  install      Install python dependencies"
	@echo "  run          Run FastAPI development server"
	@echo "  test         Run test suite with pytest"
	@echo "  lint         Lint and format code using ruff"
	@echo "  migrate      Run alembic database migrations"
	@echo "  sample       Process both supplied sample PDFs"
	@echo "  docker-up    Start full stack with Docker Compose"
	@echo "  docker-down  Stop Docker Compose stack"

install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check .

migrate:
	alembic upgrade head

sample:
	python scripts/process_sample.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
