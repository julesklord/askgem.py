# DESIGN.md - mentask.py

## Architecture Overview
mentask is a Python-based multi-task AI assistant and orchestration CLI. It leverages modern Python tooling (uv, tox, ruff, pytest).

## Core Components
- **Orchestrator:** Manages tasks and agent workflows.
- **Tools Registry:** Secure file and system operations via TrustManager.
- **CLI Interface:** Provides a terminal-based UI for interacting with the assistant.
