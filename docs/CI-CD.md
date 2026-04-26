# CI/CD Pipeline Documentation

This document describes the automated testing, security scanning, and release workflows that power **mentask**'s continuous integration and deployment.

---

## Overview

**mentask** uses **GitHub Actions** to automate three critical workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Python CI** | Push, Pull Request | Lint, security audit, tests (Python 3.13) |
| **Security Scan** | Push, Pull Request | Secret detection (gitleaks) |
| **Release** | Tag push (v*) | Build & publish to PyPI |

---

## Workflow 1: Python CI (`.github/workflows/python-ci.yml`)

### Trigger

Runs on **every push** and **pull request** to any branch.

### Stages

#### 1. Checkout & Setup
```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v4
  with:
    python-version: '3.13'
```
- Clones the repository
- Installs Python 3.13 on Ubuntu Linux

#### 2. Lint (Ruff)
```yaml
- run: ruff check .
```
- **What it checks:** Code style, import ordering, unused imports, complexity
- **Replacement for:** flake8, isort, black (all in one tool)
- **Fail condition:** Any style violation stops the workflow

#### 3. Security Audit (pip-audit)
```yaml
- run: pip-audit
```
- **What it checks:** Known CVEs in dependency tree
- **Fail condition:** Any critical/high vulnerability detected

#### 4. Test Suite (pytest)
```yaml
- run: |
    pip install -e .[dev]
    export PYTHONPATH=$(pwd)/src && pytest tests/
```
- **What it checks:** All unit & integration tests
- **Coverage:** CLI, orchestration, managers, tools, security
- **Fail condition:** Any test failure

### Local Equivalent

To run the same CI checks locally:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all CI steps
ruff check .
pip-audit
export PYTHONPATH=$(pwd)/src && pytest tests/ -v
```

Or use `tox` to test across Python 3.10–3.13:

```bash
tox
```

---

## Workflow 2: Security Scan (`.github/workflows/security.yml`)

### Trigger

Runs on **every push** and **pull request**.

### Stage: Gitleaks Scan
```yaml
- uses: gitleaks/gitleaks-action@v2
```
- **What it checks:** Git history for exposed secrets (API keys, tokens, passwords)
- **Database:** Continuously updated secret patterns
- **Fail condition:** Any secret detected in staged/committed code

### Local Equivalent

To scan locally:

```bash
# Install gitleaks (requires Go or Docker)
# Via Homebrew: brew install gitleaks
# Via Docker: docker run zricethezav/gitleaks:latest detect --source .

gitleaks detect --source . -v
```

### Best Practices

- **Never commit secrets.** Use `keyring` module (see `src/mentask/core/paths.py`)
- **Rotate credentials** if accidentally committed
- **Use `.gitignore`** to block `.env`, `*.key`, `config/*.yml` with real creds

---

## Workflow 3: Release (`.github/workflows/release.yml`)

### Trigger

Runs when a **tag matching `v*`** is pushed (e.g., `git push origin v0.13.4`).

### Prerequisites

1. **Version must be updated** in `pyproject.toml`
2. **Changelog must be updated** in `CHANGELOG.md`
3. **Tag must match version** (e.g., version `0.13.4` → tag `v0.13.4`)

### Stages

#### 1. Checkout & Setup
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history for release notes
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
```

#### 2. Build Package
```yaml
- run: python -m build
```
- Generates `dist/mentask-0.13.4-py3-none-any.whl`
- Generates `dist/mentask-0.13.4.tar.gz`

#### 3. Create GitHub Release
```yaml
- uses: softprops/action-gh-release@v2
  with:
    files: dist/*
    generate_release_notes: true
```
- Creates a GitHub Release page
- Attaches built wheels and source distributions
- Auto-generates release notes from PR commits

#### 4. PyPI Publishing (Optional)
The current workflow does **not** auto-publish to PyPI. To add:

```yaml
- name: Publish to PyPI
  run: |
    pip install twine
    twine upload dist/* -u __token__ -p ${{ secrets.PYPI_TOKEN }}
```

---

## Local Release Process (Before Pushing Tags)

### 1. Update Version & Changelog

```bash
# Edit pyproject.toml
# - version = "0.13.5"

# Edit CHANGELOG.md
# - Add ## [0.13.5] - 2026-04-20
# - Summarize changes

git add pyproject.toml CHANGELOG.md
git commit -m "release: bump version to 0.13.5"
```

### 2. Tag & Push

```bash
# Create annotated tag
git tag -a v0.13.5 -m "Release version 0.13.5"

# Push to GitHub
git push origin main
git push origin v0.13.5  # This triggers the Release workflow

# Or push together
git push origin --all --follow-tags
```

### 3. Monitor Release Workflow

- Go to **GitHub → Actions → Release**
- Wait for workflow to complete (~2-3 minutes)
- Verify release on **GitHub → Releases**
- Check that artifacts (wheel, sdist) are attached

---

## Branch Protection Rules

The following **branch protection rules** should be enforced on `main`:

- ✅ Require pull request reviews (1 approval minimum)
- ✅ Require status checks to pass:
  - `Python CI (Pro)` — lint, audit, tests
  - `Security Scan` — gitleaks
- ✅ Require branches to be up to date before merging
- ✅ Allow auto-merge (for CI/CD automation)

---

## Debugging CI Failures

### If Python CI fails:

1. **Lint error?**
   - Run `ruff check src/ tests/` locally
   - Review Ruff output for specific files/lines
   - Fix with `ruff format` or manually

2. **Audit error?**
   - Run `pip-audit` locally
   - Review security advisories
   - Update dependencies or add allowlist if false positive

3. **Test error?**
   - Run `pytest tests/ -v` locally to reproduce
   - Check specific test output for assertion details
   - Fix the code or test

### If Security Scan fails:

1. Review gitleaks output in workflow logs
2. Identify the exposed secret in git history
3. **Do NOT ignore** — rotate credentials immediately
4. Use `git filter-repo` or similar to remove from history
5. Force-push (only if on a branch, not `main`)

### If Release fails:

1. Check that `pyproject.toml` version matches tag (e.g., tag `v0.13.4`, version `0.13.4`)
2. Ensure no uncommitted changes in `dist/` or build artifacts
3. Verify PyPI token (if publishing)

---

## Environment Variables & Secrets

### GitHub Secrets Used

| Secret | Used In | Purpose |
|--------|---------|---------|
| `GITHUB_TOKEN` | All workflows | Authenticate GitHub API (auto-provided) |
| `PYPI_TOKEN` | Release (optional) | Publish to PyPI (not currently enabled) |

### Local Environment for Testing

```bash
# Set Gemini API key (required for integration tests)
export GEMINI_API_KEY="your-api-key-here"

# Run with simulation (mocked, no API calls)
export mentask_SIMULATION_MODE=true
pytest tests/ -v
```

---

## Extending the Pipelines

### Add a New Step to Python CI

Edit `.github/workflows/python-ci.yml`:

```yaml
- name: My Custom Check
  run: |
    python scripts/my_check.py
```

### Add a New Test Environment

Update `tox.ini`:

```ini
[tox]
envlist = py310, py311, py312, py313, py314, lint

[testenv:py314]
deps =
    pytest>=8.0.0
    ...
commands =
    pytest tests/ -v {posargs}
```

### Add Automatic Publishing to PyPI

Edit `.github/workflows/release.yml` and add:

```yaml
- name: Publish to PyPI
  run: |
    pip install twine
    twine upload dist/* -u __token__ -p ${{ secrets.PYPI_TOKEN }}
```

Then add `PYPI_TOKEN` to GitHub Secrets.

---

## References

- **Workflow files:** [.github/workflows/](.github/workflows/)
- **Ruff documentation:** [astral-sh/ruff](https://github.com/astral-sh/ruff)
- **GitHub Actions:** [github.com/features/actions](https://github.com/features/actions)
- **Gitleaks:** [zricethezav/gitleaks](https://github.com/zricethezav/gitleaks)
