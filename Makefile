.PHONY: help install test lint format security clean docker-dev docker-prod

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies with Poetry"
	@echo "  make test          - Run tests with coverage"
	@echo "  make lint          - Run all linters (pylint, mypy, black, isort)"
	@echo "  make format        - Format code with black and isort"
	@echo "  make security      - Run security checks with bandit"
	@echo "  make pre-commit    - Install pre-commit hooks"
	@echo "  make clean         - Clean up generated files"
	@echo "  make docker-dev    - Build and run development Docker container"
	@echo "  make docker-prod   - Build and run production Docker container"
	@echo "  make all           - Run format, lint, security, and test"

install:
	poetry install

test:
	poetry run pytest tests/ -v --cov=revolut_edavki --cov-report=term-missing --cov-report=html

lint:
	@echo "Running Black check..."
	poetry run black --check .
	@echo "Running isort check..."
	poetry run isort --check-only .
	@echo "Running Pylint..."
	poetry run pylint revolut_edavki/ --exit-zero
	@echo "Running Mypy..."
	poetry run mypy revolut_edavki/ --ignore-missing-imports

format:
	@echo "Formatting with Black..."
	poetry run black .
	@echo "Sorting imports with isort..."
	poetry run isort .

security:
	@echo "Running Bandit security scan..."
	poetry run bandit -r revolut_edavki/ -ll

pre-commit:
	poetry run pre-commit install
	@echo "Pre-commit hooks installed"

clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf *.xml
	rm -rf debug_*.csv
	rm -rf uploads/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docker-dev:
	docker-compose --profile dev up --build

docker-prod:
	docker-compose --profile production up --build

all: format lint security test
	@echo "All checks passed!"
