# FastAPI LangGraph Template - Makefile for development and code quality

.PHONY: help install install-dev format lint test coverage quality clean run

# Default target
help:
	@echo "FastAPI LangGraph Template - Available Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  format         Format code with Black and isort"
	@echo "  lint           Run linting with Ruff"
	@echo "  quality        Run comprehensive quality checks"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests"
	@echo "  test-unit      Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  coverage       Run tests with coverage report"
	@echo ""
	@echo "Development:"
	@echo "  run            Run development server"
	@echo "  clean          Clean temporary files and caches"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install --dependency-groups dev,test
	pre-commit install

# Code quality targets
format:
	@echo "🎨 Formatting code with Black and isort..."
	black app tests scripts --line-length 119
	isort app tests scripts --profile black --line-length 119
	@echo "✅ Code formatting completed"

lint:
	@echo "🔍 Linting code with Ruff..."
	ruff check app tests scripts

quality:
	@echo "📊 Running comprehensive quality checks..."
	python scripts/code_quality.py --all --report quality-report.txt

# Testing targets
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

coverage:
	@echo "📈 Running tests with coverage..."
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Development targets
run:
	@echo "🚀 Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Utility targets
clean:
	@echo "🧹 Cleaning temporary files and caches..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@echo "✅ Cleanup completed"

# CI targets (for GitHub Actions)
ci-quality:
	@echo "🤖 Running CI quality checks..."
	black --check app tests scripts --line-length 119
	isort --check-only app tests scripts --profile black --line-length 119
	ruff check app tests scripts
	python scripts/code_quality.py --all --fail-on-score 7.0

# All-in-one targets
check: format lint test
	@echo "✅ All checks completed successfully!"

setup: install-dev
	@echo "✅ Development environment setup completed!"