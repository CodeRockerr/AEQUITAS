# ═══════════════════════════════════════════════════════════════
#  AEQUITAS — Makefile
#  Usage: make <target>
#  Run `make help` to see all available commands.
# ═══════════════════════════════════════════════════════════════

.PHONY: help dev down logs build test lint format typecheck \
        migrate migrate-create shell-backend shell-db clean

# ── Colours for pretty output ─────────────────────────────────
BOLD  := \033[1m
GREEN := \033[32m
CYAN  := \033[36m
RESET := \033[0m

# ─────────────────────────────────────────────────────────────
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)AEQUITAS — available commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; \
		{printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─────────────────────────────────────────────────────────────
#  LOCAL DEVELOPMENT
# ─────────────────────────────────────────────────────────────

dev: ## Start all services locally (Postgres, Redis, backend, frontend)
	@echo "$(GREEN)Starting AEQUITAS...$(RESET)"
	docker compose -f infra/docker-compose.yml up --build

dev-detached: ## Start all services in the background
	docker compose -f infra/docker-compose.yml up --build -d

down: ## Stop all running services
	docker compose -f infra/docker-compose.yml down

down-volumes: ## Stop all services AND delete data volumes (clean slate)
	docker compose -f infra/docker-compose.yml down -v

logs: ## Tail logs from all services
	docker compose -f infra/docker-compose.yml logs -f

logs-backend: ## Tail backend logs only
	docker compose -f infra/docker-compose.yml logs -f backend

logs-frontend: ## Tail frontend logs only
	docker compose -f infra/docker-compose.yml logs -f frontend

build: ## Rebuild all Docker images without cache
	docker compose -f infra/docker-compose.yml build --no-cache

# ─────────────────────────────────────────────────────────────
#  BACKEND — code quality
# ─────────────────────────────────────────────────────────────

lint: ## Run Ruff linter on the backend
	cd backend && ruff check app tests

format: ## Auto-format backend code with Ruff
	cd backend && ruff format app tests

typecheck: ## Run Mypy static type checker
	cd backend && mypy app

check: lint typecheck ## Run lint + typecheck together (use before committing)

# ─────────────────────────────────────────────────────────────
#  TESTING
# ─────────────────────────────────────────────────────────────

test: ## Run all backend tests
	cd backend && pytest tests/ -v

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit/ -v

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration/ -v

test-coverage: ## Run tests with coverage report
	cd backend && pytest tests/ --cov=app --cov-report=term-missing

# ─────────────────────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────────────────────

migrate: ## Apply all pending database migrations
	cd backend && alembic upgrade head

migrate-down: ## Roll back the last migration
	cd backend && alembic downgrade -1

migrate-create: ## Create a new migration (usage: make migrate-create name=add_signals_table)
	cd backend && alembic revision --autogenerate -m "$(name)"

migrate-history: ## Show migration history
	cd backend && alembic history --verbose

# ─────────────────────────────────────────────────────────────
#  SHELL ACCESS
# ─────────────────────────────────────────────────────────────

shell-backend: ## Open a shell inside the running backend container
	docker compose -f infra/docker-compose.yml exec backend bash

shell-db: ## Open a psql shell inside the running Postgres container
	docker compose -f infra/docker-compose.yml exec db \
		psql -U aequitas -d aequitas

shell-redis: ## Open a redis-cli shell
	docker compose -f infra/docker-compose.yml exec redis redis-cli

# ─────────────────────────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────────────────────────

install-backend: ## Install backend Python dependencies into venv
	cd backend && python3 -m venv .venv && \
		.venv/bin/pip install --upgrade pip && \
		.venv/bin/pip install -e ".[dev]"

install-frontend: ## Install frontend Node dependencies
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies

setup: ## First-time project setup (copy .env, install deps)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN).env created from .env.example — fill in your real values$(RESET)"; \
	else \
		echo ".env already exists — skipping"; \
	fi
	$(MAKE) install

# ─────────────────────────────────────────────────────────────
#  CLEAN
# ─────────────────────────────────────────────────────────────

clean: ## Remove all build artefacts, caches, and compiled files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(RESET)"
