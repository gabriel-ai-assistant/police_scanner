.PHONY: help install test lint format build up down restart clean logs db-migrate db-shell

.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install all dependencies (Python + Frontend)
	@echo "Installing Python dependencies..."
	@pip install -r app_api/requirements.txt
	@pip install -r app_scheduler/requirements.txt
	@pip install -r app_transcribe/requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "✓ All dependencies installed"

test: ## Run all test suites
	@echo "Running Python tests..."
	@pytest app_api/tests/ app_scheduler/tests/ app_transcribe/tests/ -v
	@echo "Running frontend tests..."
	@cd frontend && npm test
	@echo "✓ All tests passed"

test-backend: ## Run backend tests only
	@pytest app_api/tests/ app_scheduler/tests/ app_transcribe/tests/ -v

test-frontend: ## Run frontend tests only
	@cd frontend && npm test

test-coverage: ## Run tests with coverage report
	@pytest --cov=app_api --cov=app_scheduler --cov=app_transcribe --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

lint: ## Run all linters
	@echo "Linting Python code..."
	@ruff check .
	@echo "Linting frontend code..."
	@cd frontend && npm run lint
	@echo "✓ Linting complete"

format: ## Auto-format all code
	@echo "Formatting Python code..."
	@ruff format .
	@echo "Formatting frontend code..."
	@cd frontend && npm run format
	@echo "✓ Formatting complete"

type-check: ## Run type checking
	@echo "Type checking Python..."
	@mypy app_api app_scheduler app_transcribe
	@echo "Type checking TypeScript..."
	@cd frontend && npm run type-check
	@echo "✓ Type checking complete"

##@ Docker Operations

build: ## Build all Docker containers
	@echo "Building Docker containers..."
	@docker compose build
	@echo "✓ Containers built successfully"

up: ## Start all services
	@echo "Starting all services..."
	@docker compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "Access points:"
	@echo "  Frontend: http://localhost:80"
	@echo "  API:      http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "Stopping all services..."
	@docker compose down
	@echo "✓ Services stopped"

restart: down up ## Restart all services

logs: ## Tail logs for all services
	@docker compose logs -f

logs-api: ## Tail API logs
	@docker compose logs -f scanner-api

logs-scheduler: ## Tail scheduler logs
	@docker compose logs -f app-scheduler

logs-transcribe: ## Tail transcription logs
	@docker compose logs -f scanner-transcription

ps: ## Show running containers
	@docker compose ps

##@ Database Operations

db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	@python db/scripts/execute-migrations.py
	@echo "✓ Migrations complete"

db-shell: ## Open PostgreSQL shell
	@docker compose exec -it scanner-api psql -h $(PGHOST) -U $(PGUSER) -d $(PGDATABASE)

db-backup: ## Create database backup
	@echo "Creating database backup..."
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	docker compose exec scanner-api pg_dump -h $(PGHOST) -U $(PGUSER) $(PGDATABASE) > db/backups/backup_$$timestamp.sql
	@echo "✓ Backup created in db/backups/"

##@ Cleanup

clean: ## Clean build artifacts and temp files
	@echo "Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@cd frontend && rm -rf dist/ build/ .vite/ 2>/dev/null || true
	@echo "✓ Cleanup complete"

clean-all: clean ## Clean everything including Docker volumes
	@echo "Removing Docker volumes..."
	@docker compose down -v
	@echo "✓ Full cleanup complete"

##@ Utilities

shell-api: ## Open shell in API container
	@docker compose exec scanner-api /bin/bash

shell-scheduler: ## Open shell in scheduler container
	@docker compose exec app-scheduler /bin/bash

shell-transcribe: ## Open shell in transcription container
	@docker compose exec scanner-transcription /bin/bash

health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8000/api/health | jq . || echo "API: DOWN"
	@curl -s http://localhost:7700/health | jq . || echo "MeiliSearch: DOWN"
	@docker compose exec redis redis-cli ping || echo "Redis: DOWN"

dev-setup: ## First-time development environment setup
	@bash scripts/setup-dev.sh

deploy: ## Deploy to production (use with caution)
	@bash scripts/deploy.sh
