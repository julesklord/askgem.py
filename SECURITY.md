# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.31.x  | :white_check_mark: |
| 0.30.x  | :white_check_mark: |
| < 0.30  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in mentask, please report it responsibly:

1. **Do NOT open a public GitHub issue.**
2. Email security details to the maintainers (see `pyproject.toml` for contacts).
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

You can expect an initial response within **72 hours**. We will work with you to understand and address the issue before any public disclosure.

## Security Measures

- All subprocess calls are routed through `core/subprocess_safety.py` with command whitelisting.
- Sandbox execution validates commands against known dangerous patterns.
- API keys are stored locally in `~/.mentask/` and never committed to the repository.
- The REPL sandbox blocks file writes, network access, and dangerous OS operations via audit hooks.
