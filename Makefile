.PHONY: help install test lint format clean build run dev security audit
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "SaferTrade Development Commands"
	@echo "==============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	pip install -e .

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -e ".[dev]"

test: ## Run tests
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

test-fast: ## Run fast tests only
	pytest tests/ -v -m "not slow"

lint: ## Run linting (flake8, mypy)
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	mypy --ignore-missing-imports api/ engines/ intelligence/ shared/

format: ## Format code with black
	black .
	isort .

format-check: ## Check code formatting
	black --check --diff .
	isort --check-only --diff .

security: ## Run security checks
	bandit -r . -f json -o security-report.json
	safety check

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build package
	python -m build

run: ## Run SaferTrade
	python run_safertrade.py

dev: ## Run in development mode
	SAFERTRADE_ENV=development python run_safertrade.py

api: ## Start API server
	cd api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

redis: ## Start Redis server
	redis-server redis.conf

logs: ## Show recent logs
	tail -f logs/safertrade.log

logs-clean: ## Clean old logs (keep last 100MB)
	find logs/ -name "*.log" -size +100M -exec truncate -s 100M {} \;

db-backup: ## Backup databases
	mkdir -p data/backups/$(shell date +%Y%m%d_%H%M%S)
	cp data/databases/*.db data/backups/$(shell date +%Y%m%d_%H%M%S)/

audit: ## Run full project audit
	@echo "Running project health audit..."
	@echo "Directory sizes:"
	@du -sh */ | sort -hr | head -10
	@echo "\nLarge log files:"
	@find logs/ -name "*.log" -size +50M -exec ls -lh {} \;
	@echo "\nDatabase status:"
	@ls -lh data/databases/