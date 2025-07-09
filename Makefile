# DART-Planner Makefile
# Convenient commands for development and dependency management

.PHONY: help install install-dev compile compile-dev sync validate check outdated clean test test-cov lint format security docker-build docker-dev

# Default target
help:
	@echo "DART-Planner Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Dependency Management:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  compile      - Compile requirements.txt from requirements.in"
	@echo "  compile-dev  - Compile all requirement files (prod, dev, ci)"
	@echo "  sync         - Sync environment with requirements.txt"
	@echo "  validate     - Validate lockfile is up to date"
	@echo "  check        - Check for dependency conflicts"
	@echo "  outdated     - Show outdated dependencies"
	@echo ""
	@echo "Development:"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code"
	@echo "  security     - Run security checks"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build production Docker image"
	@echo "  docker-dev   - Build development Docker image"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean        - Clean build artifacts"

# Dependency Management
install:
	python scripts/update_dependencies.py sync

install-dev:
	pip install -e .[dev]

compile:
	python scripts/update_dependencies.py compile

compile-dev:
	python scripts/update_dependencies.py compile --all

sync:
	python scripts/update_dependencies.py sync

validate:
	python scripts/update_dependencies.py validate

check:
	python scripts/update_dependencies.py check

outdated:
	python scripts/update_dependencies.py outdated

# Development
test:
	pytest -m "not slow"

test-cov:
	pytest --cov=src --cov=dart_planner --cov-report=term-missing --cov-report=html

lint:
	flake8 src/ tests/ scripts/
	mypy src/ tests/ scripts/
	import-linter --config importlinter.ini

format:
	black src/ tests/ scripts/
	isort src/ tests/ scripts/

security:
	pip-audit
	safety check
	bandit -r src/

# Docker
docker-build:
	docker build -f demos/Dockerfile -t dart-planner:latest .

docker-dev:
	docker build -f demos/Dockerfile.dev -t dart-planner:dev .

# Maintenance
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/ 