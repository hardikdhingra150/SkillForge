# SkillForge developer commands. Run `make help` for the list.

PY      ?= python3
VENV    := backend/.venv
VPY     := $(VENV)/bin/python
BACKEND := cd backend &&

.DEFAULT_GOAL := help
.PHONY: help setup db db-down migrate seed api worker web mcp test test-backend test-web e2e lint lint-backend lint-web build check token sandbox-image secrets rotate-db-password

help: ## Show available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install frontend and backend dependencies (creates backend/.venv)
	npm install
	test -x $(VPY) || $(PY) -m venv $(VENV)
	$(VPY) -m pip install -q -r backend/requirements.txt -r backend/requirements-dev.txt

db: ## Start local Postgres (needs .env.postgres)
	docker compose up -d postgres

db-down: ## Stop local Postgres
	docker compose down

migrate: ## Apply database migrations
	$(BACKEND) .venv/bin/alembic upgrade head

seed: ## Register the built-in skills (runs their self-tests first)
	$(BACKEND) .venv/bin/python -m app.register_builtin_skills

api: ## Run the API on :8000 with reload
	$(BACKEND) .venv/bin/uvicorn app.main:app --reload --port 8000

worker: ## Run the background worker
	$(BACKEND) .venv/bin/python -m app.worker

web: ## Run the frontend dev server on :5173
	npm run dev

mcp: ## Run the MCP server on stdio (for testing; agents launch backend/bin/skillforge-mcp themselves)
	backend/bin/skillforge-mcp

test-backend: ## Run backend unit tests
	$(BACKEND) .venv/bin/python -m unittest discover tests

lint-backend: ## Lint backend Python with ruff
	$(BACKEND) .venv/bin/ruff check .

rotate-db-password: ## Set a new random Postgres password in the database and .env.postgres
	$(VPY) scripts/rotate_db_password.py

secrets: ## Scan the whole git history for leaked secrets (gitleaks, via Docker)
	docker run --rm -v "$(CURDIR):/repo:ro" zricethezav/gitleaks:v8.24.3 git /repo --no-banner --redact

sandbox-image: ## Pull the image the Docker sandbox runs skills in
	docker pull python:3.14-slim

token: ## Print a new random API_TOKEN for backend/.env
	@$(VPY) -c "import secrets; print('API_TOKEN=' + secrets.token_urlsafe(32))"

test-web: ## Run frontend unit tests (Vitest)
	npm test

e2e: ## Run Playwright smoke tests (mocked API)
	npm run test:e2e

lint-web: ## Lint frontend with ESLint
	npm run lint

lint: lint-backend lint-web ## Lint everything

build: ## Production build of the frontend
	npm run build

test: test-backend test-web ## Run all tests

check: lint test build ## Everything CI runs
