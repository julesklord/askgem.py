# Makefile for mentask project

.PHONY: install lint test typecheck security format clean

# Install dependencies (including dev)
install:
	uv sync --all-extras

# Lint code using ruff
lint:
	uv run ruff check .

# Format code using ruff (or black)
format:
	uv run ruff format .

# Run test suite
test:
	uv run pytest

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
