# Changelog — askgem

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

---

## [2.0.0] - 2026-04-01

### 🌍 Internationalization (i18n)

- **Multi-Language Engine:** Implemented `askgem.core.i18n.Translator` with OS-level locale auto-detection via `locale.getlocale()` and `LANG` environment variable override support.
- **8 Languages Supported:** Shipped full translation dictionaries for English (`en`), Spanish (`es`), French (`fr`), Portuguese (`pt`), German (`de`), Italian (`it`), Japanese (`ja`), and Chinese Simplified (`zh`).
- **String Decoupling:** Extracted all 40+ hardcoded UI strings from `query_engine.py` into locale-specific JSON files under `src/askgem/locales/`.

### 🎨 TUI Modernization

- **Welcome Dashboard Panel:** Replaced the plain-text startup with a stylized `rich.panel.Panel` showing the active model, edit mode, and detected language.
- **Interactive Prompts:** Upgraded all user inputs from raw `console.input` to `rich.prompt.Prompt` and `rich.prompt.Confirm` with built-in validation.
- **Tool Execution Spinners:** Wrapped all autonomous tool calls with `rich.status.Status` dot-spinners to provide visual feedback during processing.

### 🔧 Repository Cleanup & Audit

- **Dead File Removal:** Purged legacy artifacts (`PyGemAi.egg-info`, `prompt_drafts.md`, `.snapshots/`, stub test files).
- **Static Analysis:** Ran `ruff` across entire codebase — auto-fixed 60 formatting violations; 13 remaining are harmless style preferences in test files.
- **Dependency Health:** All dependencies confirmed up-to-date with no breaking changes.

### 📖 Documentation

- **README.md:** Complete rewrite with architecture diagram, i18n table, configuration paths, contributing guidelines, and full command reference.
- **CHANGELOG.md:** Restructured with semantic versioning and categorized entries.

---

## [2.0.0-dev2] - 2026-04-01

### Complete Redesign: Autonomous CLI Agent

- **SDK Migration:** Full migration to `google-genai>=0.2.0` with native support for `gemini-2.5-pro` and latest Google models.
- **Autonomous System Tools:** The CLI is now an agent with tools — can read/edit files on disk, execute bash commands (with 60s timeout), and explore directories.
- **Human-in-the-Loop Protection:** All destructive actions require manual confirmation by default, with mandatory `*.bkp` backup files for every edit.
- **Dual Function Detection:** Fixed streaming failures when invoking tools by implementing SDK-level detection with native fallback via `candidate.content.parts`.

### Modular Architecture

- **Layer Separation:** Clean architecture: `core/`, `engine/`, `tools/`, and `ui/`.
- **Pure JSON Configuration:** `ConfigManager` handles all settings in `~/.askgem/settings.json` with automatic persistence.
- **Legacy Cleanup:** Removed all v1.x features (encryption with `cryptography`, rigid themes, complex security) to focus on a lightweight DevOps tool.

### Context & Memory

- **Rolling Window History:** `HistoryManager` auto-saves sessions to `~/.askgem/history/` with dynamic token truncation on full context loads.

### Interface

- **Slash Commands:** Introduced `/history load|list|delete`, `/clear`, `/model`, `/mode` (auto/manual), and `/help`.
- **Streaming UI:** Enhanced with `Rich` supporting real-time Markdown and syntax highlighting without breaking intermediate tool invocations.

---

## [1.3.0] - 2026-03-29

### Senior Audit & Refactoring

- **Initial Modular Architecture:** First modularization pass in v1.3.
- **UX Fix:** Eliminated the "double printing" bug.
- **Technical Improvements:** Migration to `pyproject.toml` (from `setup.py`) and broad exception cleanup.

---

## [1.2.1] - 2026-03-29

- Minor version corrections and initial pyproject packaging.

## [1.2.0] - Prior

- Initial experimental version with profile and theme management (Deprecated).
