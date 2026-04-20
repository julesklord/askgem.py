# Welcome to the AskGem Wiki

![AskGem Banner](https://raw.githubusercontent.com/julesklord/askgem.py/main/docs/assets/banner.png)

**askgem** is a professional, autonomous command-line AI coding agent powered by Google Gemini. Reborn with the **v0.16.0** core, it features **Autonomous LSP Integration**, **Professional TUI Rendering**, and a **Hardened Trust System** designed for high-stakes technical environments.

## Quick Start

Get running in your current project in 3 commands:

```bash
# 1. Install or update to the latest version
pip install -e "."

# 2. Launch in your repo (AskGem will detect or offer to create a Workspace)
askgem

# 3. Grant trust if you need to touch files outside the CWD
/trust G:/SHARED_LIBS
```

## Wiki Index

* [Architecture](Architecture.md) — System diagram and the **AgentOrchestrator** loop.
* [Installation & Setup](Installation_and_Setup.md) — Keyring integration and security configuration.
* [Usage](Usage.md) — Workflows, **Trust System**, and Workspace management.
* [API Reference](API_Reference.md) — Public contracts, Managers, and Schemas.
* [Dependencies](Dependencies.md) — Stack breakdown and justifications.
* [Development Guide](Development_Guide.md) — **Simulation Layer** and Testing protocol.
* [Changelog](../CHANGELOG.md) — Version history and structured tracking.
