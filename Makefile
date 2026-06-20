# Makefile for mentask project

.PHONY: install lint test test-integration coverage coverage-html typecheck security format clean

# Install dependencies (including dev)
install:
	uv sync --all-extras

# Lint code using ruff
lint:
	uv run ruff check .

# Format code using ruff (or black)
format:
	uv run ruff format .

# Run test suite (excluding integration tests that require external services)
test:
	uv run pytest -m "not integration"

# Run integration tests (requires Ollama or external services)
test-integration:
	uv run pytest -m integration

# Run tests with coverage report
coverage:
	uv run pytest --cov=mentask --cov-report=term-missing -m "not integration"

# Run tests with HTML coverage report
coverage-html:
	uv run pytest --cov=mentask --cov-report=html -m "not integration"
	@echo "Coverage report generated at htmlcov/index.html"

# Run mypy static type checking
typecheck:
	uv run mypy src tests

# Run security scans (pip-audit and bandit)
security:
	uv run pip-audit
	uv run bandit -r src -ll

# Clean build artifacts
clean:
	rm -rf .venv build dist *.egg-info
