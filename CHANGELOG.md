# Changelog

All notable changes to this project will be documented in this file.

## [0.18.6] - 2026-04-26

### Changed

- **License**: Switched from GPL-3.0 to **MIT License** to improve compatibility and adoption.

## [0.18.5] - 2026-04-25

### Changed

- **Global Rebranding**: Finalized the transition from `askgem` to **mentask** across the entire codebase, documentation, and metadata.
- **Repository Metadata**: Synchronized GitHub URLs and homepage references to reflect the new `mentask` identity.
- **Version Bump**: Promoted project to `v0.18.5` to mark the completion of the branding overhaul and foundational stability fixes.

### Fixed

- **Documentation**: Corrected legacy naming in README.md and standardized "Formerly known as askgem" notices.

## [0.18.0] - "Lisan al-Gaib" - 2026-04-24

### Added

- **Multi-Model Sovereignty**: Refactored core session management to a provider-agnostic architecture, breaking the Gemini-only barrier.
- **models.dev Integration**: Integrated with the `models.dev` API for dynamic model discovery, real-time pricing, and automatic endpoint resolution.
- **OpenAI-Compatible Driver**: Support for DeepSeek, Groq, 302.AI, and other OpenAI-compatible endpoints via a lightweight `urllib` driver.
- **DeepSeek R1 Support**: Native parsing of `<think>` tags to render reasoning blocks in the TUI.
- **`ask_user` Tool**: Allows the agent to explicitly ask the user for clarification, preventing guesswork.
- **`python_repl` Tool**: Integrated a persistent Python sandbox for validating snippets and logic before application.
- **GemStyleRenderer**: Implemented a persistent, high-fidelity CLI renderer with committed buffer support, ensuring full history retention and incremental code/thought rendering.
- **Intelligence Tools**: Added `WorkingMemoryTool` for inter-turn semantic state and `PlanTool` for persistent execution plan checkpointing.
- **UX Commands**: New `/theme` (dynamic color schemes), `/artifacts` (interactive tool results browsing), and `/undo` (rollback file modifications) commands.
- **Self-Critique Loop**: Integrated a "System Reflection" loop that triggers upon tool failures, forcing the agent to re-evaluate its strategy.
- **Safety**: Added automatic backups before any `write_file` or `edit_file` operation.
- **CLI Discovery**: Added `/discover` command to search and compare models across 115+ providers.

### Fixed

- **Memory Management**: Fixed memory leaks in long sessions by limiting the `artifacts` buffer and implementing dynamic context thresholds based on model limits.
- **Architecture**: Refactored `compress_history` to follow the standard `ProviderManager` flow.
- **UI**: Standardized all timing and icons for a premium, consistent feel.

## [0.17.4] - 2026-04-24

### Changed

- **UI Design**: Redesigned the `CliRenderer` interface to match the Gemini CLI aesthetic. Removed all italic fonts, added Unicode status icons (`✦`, `⚡`, `✓`, `✗`, `⚠`) with ASCII fallbacks for legacy Windows consoles, and made tool call displays compact and clean.
- **Security Hardening**: Implemented the "System Guardian" trait. The agent now actively protects critical files (like `uv.lock`, `.gitignore`, `.env`, `.git`) and will generate explicit red security warnings if operations attempt to modify them.
- **Project Hygiene**: Added specific system prompt instructions strictly prohibiting the alteration or deletion of operational metadata and lockfiles.

## [0.17.3] - 2026-04-20

### Fixed

- **Artifact Expansion**: Resolved ANSI escape sequence corruption on Windows when expanding artifacts via `Ctrl+O` while the prompt is active (using `patch_stdout`).
- **Highlighting**: Added syntax highlighting support for `write_file` results and ensured LSP diagnostics markup is rendered correctly.

## [0.17.2] - 2026-04-20

### Changed

- **Logging**: Migrated internal `print` statements in `LSPClient` and `HistoryManager` to `logging.info/error` for better observability and professional output control.
- **UI**: Standardized all user-facing output to use `console.print` through the `CliRenderer` system.

## [0.17.1] - 2026-04-20

### Fixed

- **CLI**: Resolved `AttributeError` when using `prompt_toolkit` by correctly awaiting the asynchronous prompt before stripping whitespace.

## [0.17.0] - 2026-04-20

### Added

- **Real-time Shell Streaming**: `execute_bash` now streams output line-by-line to a live terminal panel.
- **Artifact Expansion**: Added `Ctrl+O` keybinding to expand/collapse tool outputs.
- **Improved UX**: Navigation with `Tab` and artifact IDs (`#1`, `#2`, etc.) in tool results.
- **Dependency**: Added `prompt-toolkit` for advanced interactive CLI features.

### Changed

- **Refined Security**: SAFE commands (echo, ls, git status) no longer require confirmation in non-trusted dirs.
- **Architecture**: Modularized LSP client into `ExecutionManager`.
- **Async Trust**: `load_trust` is now an asynchronous operation.

### Fixed

- **BOM Error**: Removed non-printable BOM characters causing SyntaxError in Windows.
- **History Deserialization**: Fixed Pydantic validation errors when metadata is missing in history files.
- **Test Suite**: Resolved multiple regressions in HistoryManager, TrustManager, and LSP tests.

## [2.1.1] - 2026-04-03

### Changed

- Changed: Merge pull request #5 from julesklord/develop (d6d66ea)
- Changed: docs: Standardized console.py docstrings to Google-style (a94cf81)
- Changed: test: Resolved remaining ruff linter warnings in test suite (78d3f17)
- Changed: refactor: Extracted function call detection to helper and cleaned up _stream_response (b36af44)
- Changed: docs: Standardized core logic docstrings to Google-style (cbfcdb7)
- Changed: perf: Added character-based truncation to read_file (ed98146)
- Changed: chore: Resolve merge conflict in README.md by adopting main branding (85a3a4f)
- Changed: style: Finalize global branding synchronization (2000s Classic) across core, agent, and docs (0b2fe1d)
- Changed: chore: Full Project Rebrand Integration (Local Only) (a5e2ce8)
- Changed: style: Replace hero banner with ultra-minimalist 2000s design (6f99173)
- Changed: docs: Update README and assets with Friendly Prism mascot and Google color badges (c7c93f0)
- Changed: ui: Redesign welcome dashboard with ASCII mascot and Google colors (b7dcb70)
- Changed: refactor: Apply brand theme to chat agent UI (User=Yellow, Agent=Blue) (8a02071)
- Changed: style: Implement Google Identity Theme in CLI (Blue/Yellow) (c72d535)
- Changed: docs: Fix heading and list spacing in README.md (e933cf0)
- Changed: style: Align table columns in ROADMAP.md (e78f45e)
- Changed: docs: Improve module docstrings in paths.py (829f6c2)
- Changed: chore: Professional refactor v2.1.0 - Modular architecture, Token Economy, and Wiki docs (064db00)
- Changed: docs: professional cleanup and documentation update for v2.1.0 (9d7ca58)
- Changed: edit gitignore (9b4ffd2)
- Changed: docs: overhaul README.md and integrate project wiki v0.8.0 (7e04ff9)
- Changed: Merge pull request #4 from julesklord/develop (af08683)
- Changed: chore: reset project versioning to 0.8.0 (pre-release) (f8b518e)
- Changed: refactor: extract path utilities, add docstrings to i18n and config modules, and add sample script (e664b71)
- Changed: chore: bump version to 2.1.0 (4d675e1)
- Changed: docs: add project wiki and usability diagnostic suite (9691525)
- Changed: perf: optimize token usage with compact prompts and rolling history window (52a3a3a)
- Changed: ci: add automated deployment workflow for GitHub and PyPI (a80f2a2)
- Changed: refactor: finalize transition to modular architecture (cli, agent, core) (238b193)
- Changed: chore: clean repo root — remove legacy Docker boilerplate, dead config files, expand .gitignore for v2.0 release (011f207)
- Changed: Update README to include Claude as a contributor (a3f089e)
- Changed: Update project name in README.md (761456d)
- Changed: Rename project in README (881bbec)
- Changed: docs: add roadmap overview to README and create detailed ROADMAP.md file (b71a4ec)
- Changed: refactor: remove legacy documentation and configuration files and update gitignore patterns (bb167e9)
- Changed: docs: remove outdated version 1.2.1 documentation and initialize project structure (fab4d87)
- Changed: refactor: remove unused files (2941cee)
- Changed: Feat: Add chat profiles, themes, and enhance UX for v1.2.1 (3ef7ebc)
- Changed: Update .gitignore (1624034)
- Changed: Merge pull request #2 from julesklord/review-documentation-packaging (e297f51)
- Changed: Refactor: Prepare for new release and add publishing guide. (36c7ef8)
- Changed: Merge pull request #1 from julesklord/review-documentation-packaging (19a9f03)
- Changed: Refactor: Update documentation and project configuration. (a89e4a5)
- Changed: changelog changes V.1.2 (d1f8a09)
- Changed: Updates to upload v.1.2.0 to pypi.org (8862a37)
- Changed: corrections in readme (fc8772d)
- Changed: added screns (c1572ee)
- Changed: v1.2 released (b5fd3d1)
- Changed: changes in readme. (2a9afb5)
- Changed: Merge branch 'main' of <https://github.com/julesklord/PyGemAi> (9a572e8)
- Changed: Changes in doc. (107b8d4)
- Changed: Delete .github/workflows directory (9098f77)
- Changed: added instalation from pypi (pip) (4a97c28)
- Changed: changes in doc. (8a8b00a)
- Changed: uploaded to pypi (0535bce)
- Changed: changes in readme.md (3a257bb)
- Changed: changes in name of script to download (31e3e7a)
- Changed: changes in guide of use location (e9d0f21)
- Changed: deleted directories (06eb012)
- Changed: Create python-app.yml (e73e448)
- Changed: changes in semantic (33cc1ee)
- Changed: Little changes in documentation (ea56dc6)
- Changed: changes in guide of use (d8d7428)
- Changed: added vsc and writterside folders to ignore (29e3390)
- Changed: added badges and english version (20a9db7)
- Changed: Changes in Readme (21666fa)
- Changed: documentation updated (fc83d60)
- Changed: added documentation (17c4e57)
- Changed: v 0.1.4 - public alpha (7db8546)

### Added

- Added: feat: [Milestone 2] Fully Operational - Advanced Search & Diff Previews (c334c4c)
- Added: feat: [Milestone 2] Advanced Search Tools & Agentic Refactor (2746608)
- Added: Merge feature/v2.0-rewrite: mentask v2.0.0 stable release — agentic loop, i18n, rich TUI, retry logic, repo cleanup (1c691b7)
- Added: feat: add multi-language support by creating localization files for fr, it, ja, pt, zh, and de (ffa7e40)
- Added: feat: implement QueryEngine with autonomous tool dispatch and streaming support (08689f5)
- Added: Merge pull request #3 from julesklord/feature/v2.0-rewrite (8a2e607)
- Added: Merge branch 'main' into feature/v2.0-rewrite (2fdab37)
- Added: feat: add internationalization support for multiple languages and bump version to 2.0.0 (2a92979)
- Added: feat: rebrand project to mentask and implement modular architecture with internationalization support (2800870)
- Added: feat: implement cross-platform system tools for directory listing and shell command execution with unit tests (7776991)
- Added: feat: migrate to SDK v2.0 with autonomous system/file tools and modular architecture (59d5e4b)
- Added: feat: implement file system tools, shell execution, and persistent session history management (83b7894)
- Added: feat: initialize project structure and core components (5c258d1)
- Added: feat: implement autonomous agentic query engine with tool execution and configuration management (54455a3)
- Added: feat: implement core engine with Google GenAI SDK integration, autonomous tool execution, and configuration management (bb93aca)
- Added: feat: modularize CLI architecture and implement theme-based UI and security features (641956b)

### Fixed

- Fixed: docs: Comprehensive repair and lint fix for ROADMAP.md (7e3b50c)
- Fixed: docs: Update architecture diagram to mermaid and fix spacing (d96808a)
- Fixed: fix: remove duplicate version field (0eb2ddd)
- Fixed: fix(tools): improve list_directory resilience and enable edit_file on empty files (449657d)

## [0.9.0] - 2026-04-06

### Fixed

- Fixed: fix: correct path traversal logic and error messages (9dcb7d2)
- Fixed: fix: add robust keyring fallback in config manager (15f26bd)
- Fixed: sec: implement path traversal protection in file tools (abe5e2f)
- Fixed: 🔒 fix(security): Path Traversal Bypass in file tools (#35) (5ec3dd7)
- Fixed: Merge pull request #18 from julesklord/fix-execute-bash-shell-true-7236891312369897375 (34d9395)
- Fixed: Merge pull request #16 from julesklord/fix-bare-exception-memory-manager-11318845627837470644 (71cdb94)
- Fixed: fix(security): resolve command injection risk in system_tools by removing shell=True (bf0a904)
- Fixed: chore: fix bare exception handling in memory_manager.py (266391b)
- Fixed: 🧪 Add tests for MissionManager and fix import bug in test_system_tools (1b9661d)
- Fixed: sec: implement path traversal protection in file tools (fed211f)
- Fixed: fix(tools): normalize path separators to forward slashes in search results (027e26d)
- Fixed: fix(agent): stabilize streaming loop and refine function extraction (a2bc110)
- Fixed: fix(cli): improve dashboard init_api error handling and auth feedback (ee9f0d0)
- Fixed: refactor(v2.3.0): code cleanup, linting fixes, and version synchronization (909424b)
- Fixed: fix(dashboard): implement multi-state mascot and compact layout (dde8d7a)

### Changed

- Changed: docs: update README to mention sandboxed agent (a3aa338)
- Changed: refactor: split _stream_response into parsing, execution, and UI layers (5e9dde2)
- Changed: Merge pull request #65 from julesklord:palette/tui-busy-state-12103588579909134441 (b9b4394)
- Changed: 🎨 Palette: add busy state to TUI input during init (b2956c0)
- Changed: docs: add migration note detailing the reorganization of test files and project scripts (5e7a574)
- Changed: docs: add CHANGES.md tracking file migrations (92963e2)
- Changed: refactor: restructure core tests to match src directory (6ccba41)
- Changed: refactor: restructure cli tests to match src directory (8c6491a)
- Changed: refactor: restructure agent tests to match src directory (e301fe9)
- Changed: refactor: move tasks.md to docs directory (0f08c82)
- Changed: refactor: isolate ad-hoc scripts from repository root and test suites (99d0254)
- Changed: Merge pull request #55 from julesklord:docs/api-contracts (cdfe1e0)
- Changed: docs: add comprehensive Google-style docstrings (4e7af11)
- Changed: ✨ Refactor ToolDispatcher to use inspect.iscoroutinefunction for coroutine checks ✨ Add integration test for ChatAgent tool usage and mock chat session ✨ Enhance test coverage for path traversal prevention and safe path resolution ✨ Improve test for list_directory to handle empty directories ✨ Add timeout and output truncation tests for execute_bash function ✨ Implement edge case tests for is_safe_url function (d2ae942)
- Changed: ✨ Agregar archivo de configuración de agente de depuración de Python a .gitignore (76f0ea4)
- Changed: ✨ Refactor web_search and_duckduckgo_search to use asyncio.to_thread for improved performance (f54e8f2)
- Changed: ✨ Refactor ToolDispatcher tests to use mock configuration for improved isolation and localization (77dc111)
- Changed: ✨ Refactor tests to use await for web_search and web_fetch functions (44046e5)
- Changed: ✨ Refactor ToolDispatcher tests to use mock configurations for edit modes (d904db5)
- Changed: 🛡️ Sentinel: [CRITICAL] Fix SSRF / Local File Read vulnerability (#44) (0f07ffe)
- Changed: Add tests for ChatAgent core methods (#52) (b07c5b0)
- Changed: Merge pull request #7 from julesklord/jules/improve-i18n-testing-7442668985476274200 (17af31c)
- Changed: Resolve merge conflicts and modernize web_fetch to async (bed3bc9)
- Changed: Resolve merge conflict in system_tools.py (93d5c84)
- Changed: Resolve merge conflicts in file_tools.py (5d39d3a)
- Changed: Resolve merge conflict in search_tools.py (760565a)
- Changed: chore: remove unused imports in system_tools.py and use contextlib.suppress (#34) (3497b4c)
- Changed: 🧪 Add tests for identity manager (#50) (7e28ddf)
- Changed: 🔒 Remove unencrypted legacy API key fallback in ConfigManager (#49) (6775d66)
- Changed: 🧪 [testing] add tests for cli/main.py (#48) (d5abafb)
- Changed: 🧹 [Code Health] Simplify ToolDispatcher **init** parameters (#45) (dec6253)
- Changed: Add tests for ToolDispatcher in tools_registry.py (#43) (f74d526)
- Changed: 🧪 Add tests for paths module (#42) (67d0163)
- Changed: Remove unused imports from MemoryManager (#40) (af71d6c)
- Changed: 🧪 [testing improvement] Add unit tests for TasksManager and refactor for consistency (#39) (a10b376)
- Changed: ⚡ Make web_search and web_fetch non-blocking using asyncio.to_thread (#37) (f69556b)
- Changed: 🧹 [code health improvement] Fix deprecated API usage for locale depending on Python version (#36) (f337335)
- Changed: 🧪 Add tests for ChatAgent core loop logic (#33) (454fa59)
- Changed: ⚡ Optimize web tools to be non-blocking (#29) (845dcc0)
- Changed: 🧹 [code health improvement] Refactor execute_bash to extract process creation (#28) (6a3d403)
- Changed: 🧹 [core] Replace bare exceptions with OSError in mission_manager.py (#27) (9406b7f)
- Changed: 🧪 Add testing coverage for ToolDispatcher in agent/tools_registry.py (#26) (b2fe32a)
- Changed: 🧹 Refactor grep_search to use helper function (#25) (dfefa46)
- Changed: 🧹 refactor: Extract helper methods in main.py to improve code health (#24) (2fcb226)
- Changed: 🧹 [Code Health] Replace bare except Exception with OSError in MissionManager (#23) (df0422b)
- Changed: 🧹 Fix unused imports and formatting in memory_manager.py (#22) (3ba3178)
- Changed: Fix bare exception handling in memory_manager.py (#21) (74f7c54)
- Changed: 🧹 Remove unused Optional import in memory_manager.py (#20) (47999ca)
- Changed: Merge pull request #32 from julesklord:jules-8706320620029341882-f855cda0 (5d068c4)
- Changed: Merge branch 'main' into jules/improve-i18n-testing-7442668985476274200 (4008006)
- Changed: ✨ Refactor tests to use async/await for web_search and web_fetch functions (e5b82c4)
- Changed: 🔒 Prevent SSRF in web_fetch using IP resolution validation (37f81c4)
- Changed: ⚡ Optimize `_get_shell_args` by caching `shutil.which` (90ac45d)
- Changed: 🧹 Refactor: Extract atomic write logic to helper function in file_tools.py (567c11e)
- Changed: ⚡ perf: optimize file opening in grep_search (7f19c6e)
- Changed: chore: add branch cleanup script (b5c6891)
- Changed: Merge pull request #30 from julesklord/perf/web-tools-async-io-17104705760751454298 (ac760ab)
- Changed: Merge pull request #31 from julesklord/develop (729a8c2)
- Changed: Merge pull request #19 from julesklord/code-health-mission-manager-exception-7721112037642338980 (292183b)
- Changed: Merge main into develop and resolve conflicts using main versions (4db65e4)
- Changed: ⚡ Make web_search and web_fetch non-blocking using asyncio.to_thread (e6e61eb)
- Changed: Merge pull request #17 from julesklord:add-memory-tools-tests-10861393701788178109 (061663b)
- Changed: 🧹 [code health improvement] Replace bare exceptions with OSError in mission manager (eb25333)
- Changed: test: Add tests for memory_tools.py (3463a7e)
- Changed: Merge pull request #9 from julesklord/tests/memory-manager-error-path-11881241943984111751 (01918d4)
- Changed: Merge pull request #10 from julesklord/performance-optimize-search-loops-741017239960198109 (306dbd9)
- Changed: Merge pull request #11 from julesklord/test-memory-manager-11602269619858500549 (56e5714)
- Changed: Merge pull request #12 from julesklord/add-history-manager-tests-12289859377050965212 (3cd7b05)
- Changed: Merge pull request #14 from julesklord/add-i18n-tests-2746949307501660049 (f470dbe)
- Changed: Resolve merge conflicts with main (1b9b030)
- Changed: Merge pull request #15 from julesklord/perf-refactor-retry-keywords-15505413762355951286 (0ba15b2)
- Changed: Resolve merge conflicts with main (9403527)
- Changed: Merge branch 'main' into performance-optimize-search-loops-741017239960198109 (eca2792)
- Changed: Merge pull request #8 from julesklord/performance-optimize-search-tools-loop-2184477092077908645 (d00e5f9)
- Changed: Merge branch 'main' into performance-optimize-search-tools-loop-2184477092077908645 (b40df01)
- Changed: Merge pull request #6 from julesklord:optimize-regex-web-tools-17319507104732083970 (64df304)
- Changed: perf: refactor retryable keywords to module-level tuple (2fb67e6)
- Changed: Merge branch 'main' of <https://github.com/julesklord/mentask> (ebece5f)
- Changed: Merge pull request #13 from julesklord/test-mission-manager-17698588295635184562 (d39a53f)
- Changed: test: add unit tests for Translator in core/i18n.py (68662e8)
- Changed: Add unit tests for HistoryManager (4aace69)
- Changed: test: add unit tests for memory manager (258427e)
- Changed: ⚡ Optimize any() loop in search tools using set disjoint check (68eb08b)
- Changed: test: add coverage for memory_manager.read_memory exception path (db1a7a0)
- Changed: refactor: optimize file walk performance using set intersection (b2af2a9)
- Changed: 🧪 Add edge case tests for i18n._detect_language (0f897e0)
- Changed: perf: pre-compile regex patterns in web_tools.py (10929c7)
- Changed: docs: finalize hardening phase and cleanup audit reports (cd1f4d1)
- Changed: Context limits: truncate tool results to 10k chars (23141bb)
- Changed: docs: agregar documento de diseño para refactorización y fortalecimiento de seguridad en mentask (6e82a86)
- Changed: docs: establish official agent profiles for Smuffle and Snuggles (dc1d63e)
- Changed: Fase 4: Actualización de README con mejoras de seguridad (Keyring, Escritura Atómica) y arquitectura async (2e1fb81)
- Changed: Fase 3: Implementación de escritura atómica en edit_file para prevenir corrupción de datos (87c899a)
- Changed: Phase 2: Refactor ToolDispatcher and execute_bash for non-blocking execution (3e74e00)
- Changed: Phase 1: Integrate keyring for secure API key and settings storage (525588d)
- Changed: Merge resolve: keep local changes (ours strategy) (785930e)
- Changed: test (0e581e1)
- Changed: a (a95681b)
- Changed: chore: align CHANGELOG to 0.8.0 release (e10db00)
- Changed: x (1150a95)
- Changed: test(v2.3.0): add new unit tests for web tools, metrics, and dashboard (1d25f1b)
- Changed: build(version): official bump to v2.3.0 (7c1495e)
- Changed: docs(roadmap): synchronize milestones and update tracking for v2.3.0 (beadfa7)
- Changed: docs(roadmap): update to v2.3.0 and sanitize links (53ca9ce)

### Added

- Added: feat: truncate tool results to 10k characters (84c1b25)
- Added: feat(tui): disable input during agent turns for better UX (#54) (bae9105)
- Added: feat: register new file management tools in dispatcher (d3032cb)
- Added: feat: improve file tools (merge conflicts fix + list/del/move support) (22a32b6)
- Added: feat: agregar archivo identity.md a .gitignore (9ff31fa)
- Added: feat: implement core agent architecture, tool registry, i18n support, and CLI dashboard with comprehensive test coverage (cc9a6a8)
- Added: docs: rewrite README and update CHANGELOG to reflect project maturity and new features (75c7413)
- Added: feat: implement ChatAgent for autonomous tool dispatch and streaming model interactions (dae58db)
- Added: feat: implement ConfigManager for settings persistence and add chat agent module for core interaction logic. (1d2f57c)
- Added: feat: implement autonomous chat agent with tool routing and streaming response loop (6a7a10b)
- Added: feat: implement persistent memory and mission tracking systems with dedicated managers and tools (7a3351e)
- Added: feat: implement persistent memory and mission tracking systems with output truncation and model upgrades (bff4599)
- Added: feat: implement persistent memory and mission tracking systems with Gemini 2.5 integration (73b7754)
- Added: feat: implement persistent memory and mission tracking systems with interruption support and model update (bdef8bf)
- Added: feat: implement persistent memory and mission tracking systems with new tools and dashboard updates (1f5bf09)
- Added: feat: implement persistent memory and mission management systems with context summarization and output truncation (44ad6a2)
- Added: docs(readme): update feature list and installation for v2.3.0 (5f6bc88)
- Added: feat(cli): sync legacy mascot and bump version to 2.3.0 (7d65315)
- Added: feat(ui): implement TUI Dashboard with animated diamond mascot and debug pane (7f81b58)
- Added: feat(core): implement token and cost metrics engine (6a1e4bb)
- Added: feat(agent): support status logging and search credential injection (18f0ad9)
- Added: feat(tools): implement advanced web research (google, duckduckgo, fetch) (398c852)
- Added: feat(config): add google search support to settings (5dd2711)

## [0.16.4] - 2026-04-20

### Added

- **Project Isolation (/init)**: New command to initialize local project environments with dedicated settings, sessions, and identity files.
- **Enhanced Session Management**: Sessions are now strictly stored in `.mentask/sessions` (local) or `~/.mentask/sessions` (global) to prevent root directory clutter.
- **Improved Garbage Prevention**: Local project memory now prioritizes `.mentask/memory.md`, moving away from scattered `.mentask_knowledge.md` files.
- **Local Identity**: Support for project-specific personalities via `.mentask/identity.md`.

### Fixed

- **Path Consistency**: Centralized all operational files (usage logs, heartbeats, backups) within the `.mentask` folder hierarchy.
- **Command Help**: Added `/init` to the public help menu.

## [0.16.3] - 2026-04-20

### Description

Stabilization release focusing on CLI robustness, renderer optimizations, and multi-turn interaction stability.

### Fixed

- **CLI Robustness**: Fixed `ImportError` in `knowledge_tool.py` and resolved Windows-specific `UnicodeEncodeError`.
- **Renderer Optimization**: Eliminated "double output" and "cut-off" issues in streaming by switching to transient Live rendering and multi-turn flushing.
- **Theme System**: Fixed crashes in `/themes` command and standardized system instruction branding to "mentask".
- **Stability**: Implemented clean shutdown sequence to prevent "closed pipe" errors on Windows and ensured all background tasks are cancelled on exit.
- **Bug Fix**: Resolved `unexpected keyword argument 'tool_name'` in `CliRenderer`.

## [0.16.2] - 2026-04-20

### Fixed

- Standardized versioning to PEP 440 compliance.
- Resolved build failures in GitHub Actions.

## [0.16.1] - 2026-04-20 (Internal)

- Re-implemented Knowledge Hub as a queryable tool system.

## [0.16.0] - "The Golden Path" - 2026-04-20

### Description

Recovery and finalization of the "Bene Gesserit" initiative. This release consolidates the Professional Renderer, Stream Speed Control (Theme system), and native LSP integration into a stable build.

### Added

- **Professional Renderer**: Enhanced CLI output with theme support (Smuffle/Snuggles) and improved visual feedback.
- **Stream Speed Control**: Configurable `stream_delay` to control the pacing of agent responses.
- **LSP Auto-Check**: Integrated real-time linting diagnostics into the AgentOrchestrator loop.

### Fixed

- Fixed critical release issue where v0.15.0 was shipped as an empty commit.
- Resolved merge conflicts and synchronized versioning across all core components.
- Hardened GitHub Actions workflows with caching and multi-version Python testing.

## [0.15.0] - "Kwisatz Haderach" - 2026-04-19 (Placeholder)

### Description

Original release target for architectural hardening. Due to a technical failure, this version was shipped empty. All intended features have been recovered and delivered in v0.16.0.

## [0.14.9] - 2026-04-19

### Description

General maintenance release focusing on internal configuration schema cleanup, optimizing component-level settings, and comprehensive documentation refinement for improved developer experience.

## [0.14.8] - 2026-04-19

### Description

Architectural refinement of the AgentOrchestrator, specifically improving internal configuration propagation mechanisms and enhancing component operational stability.

## [0.14.7] - 2026-04-19

### Description

Enhanced testing infrastructure, improving unit test reliability for complex orchestration layers and enforcing stricter project-wide configuration consistency.

## [0.14.6] - 2026-04-19

### Description

Security-hardened release integrating automated vulnerability analysis (CodeQL) and formalizing linting/static analysis toolchain configurations.

## [0.14.5] - 2026-04-19

### Description

Critical infrastructure upgrade: Provisioned initial Ruff LSP client bridges and formalized agent orchestration patterns, with corresponding API contracts and technical documentation.

## [0.14.4] - 2026-04-19

### Description

Performance and reliability enhancement for LSPClient, incorporating a non-blocking background reader for asynchronous diagnostic stream capture and processing.

## [0.14.3] - 2026-04-19

### Description

Optimized LSP transport layer: transitioned to a high-concurrency, asynchronous JSON-RPC protocol implementation for reduced latency in agent-server communication channels.

## [0.14.2] - 2026-04-19

### Description

Autonomous linting framework initialization: initiated integration of LSP diagnostic loops within the AgentOrchestrator to enable real-time, event-driven code quality monitoring.

## [0.14.1] - 2026-04-19

### Description

Maintenance patch resolving repository-level configuration issues (Gitignore) and finalizing documentation for terminal-based workflow demonstration (VHS) tools.

### Fixed

- Fixed: fix: actualizar .gitignore para manejar correctamente el directorio scratch y eliminar archivo COMPLETION_SUMMARY.md (3ab6dd4)
- Fixed: fix: corregir la entrada de .gitignore para el directorio scratch (6e66e8b)

### Changed

- Changed: docs: eliminar la sección de demostración y el guion de grabación de terminal (e110d01)
- Changed: docs: add VHS terminal demo recording system and comprehensive guide (328bd58)
- Changed: Merge branch 'benegesserit' into main: v0.14.0+ LSP Integration (49ea778)
- Changed: docs(skill): add pytest/tox testing skill for AI agents (d915424)
- Changed: docs: add comprehensive agent guides, testing skill, and CI/CD documentation (b663888)
- Changed: chore: setup benegesserit branch and provision ruff v0.15.10 for LSP intelligence (77e16f2)
- Changed: upd:CHANGELOG (fcece75)

### Added

- Added: feat: agregar configuraciones para linters y herramientas de análisis, y eliminar archivo obsoleto (a8a9769)
- Added: feat: agregar archivos de configuración de CodeQL para análisis de seguridad (1f83c70)
- Added: feat:v.0.14.5-fix(public) - implement LSP client for Ruff integration and establish agent orchestration architecture with supporting documentation. (b7d057b)
- Added: feat: complete v0.14.0 'Bene Gesserit' - autonomous LSP Client Bridge integration (3b6138b)
- Added: feat: integrate LSP validation loop into AgentOrchestrator for autonomous linting (a304637)
- Added: feat: robustify LSPClient with background reader and diagnostic capture (0d28edc)
- Added: feat: implement asynchronous LSPClient with JSON-RPC transport for Ruff (7d8c245)

## [0.13.3] - 2026-04-16

### Changed

- Changed: refactor: remove unused project_context in ChatAgent identity setup (97ac8e4)
- Changed: test: remove unused local_md_path in identity manager test (88a925b)
- Changed: chore: prepare v0.13.0 Muad'Dib release (Roadmap & Version) (0ec362c)
- Changed: v0.12.3: UI Polish, Temporal Awareness, and Search/Web tools Arsenal (Sync & Cleanup) (b8ccfec)
- Changed: v0.12.3: UI Polish, Temporal Awareness, and Search/Web tools Arsenal (2c4e821)
- Changed: chore: add project banner, editor configuration, and update gitignore rules (78588cf)
- Changed: chore: ignore .mentask directory in .gitignore (13a42ca)
- Changed: upd:doc (83bc165)
- Changed: docs: upgrade wiki to v0.11.0 (Orchestra, Trust, Workspaces & Blueprint) (1c4b5cb)
- Changed: chore: sync project metadata, knowledge base and finalize cleanup for v0.11.0 (507aae9)

### Fixed

- Fixed: test: fix package import paths in test_session.py by removing src prefix (730b435)
- Fixed: v0.13.2: Purity Release - Optimized prompt architecture, fixed redundancies, and enabled full multimodal support. (e465383)
- Fixed: v0.13.1: Muad'Dib Hotfixes - Fixes persistence, security, streaming and basic crashes (393c265)

### Added

- Added: feat: stabilize v0.13.2 Purity release - 100% test pass (129/129) (0b3bccb)
- Added: feat: implement Core Knowledge Hub hierarchy (v0.13.0) and synchronize stable v0.12.3 (0d13613)
- Added: docs: overhaul README with v0.11.0 features (Workspaces, Security, Hyper-Context) (055ab07)
- Added: feat: implement core agent tools and infrastructure with supporting configuration and audit utilities (63a55d2)

## [0.11.0] - "Orchestra" - 2026-04-15

### Changed

- Changed: merge: integrate remote changes with local priority (a7808b9)
- Changed: ux: harden UI confirmations and improve token tracking metrics (e30002d)
- Changed: 🔒 Prevent plaintext API key leak on keyring failure (859eb9f)
- Changed: Merge pull request #82 from julesklord/perf-history-manager-optimization-8191261610391614523 (2cbd675)
- Changed: Merge pull request #80 from julesklord/perf/optimize-intersection-11540714724980349528 (645e27a)
- Changed: 🔒 Fix path traversal vulnerabilities in history manager (b1bc824)
- Changed: Fix linting errors that caused CI to fail (cbb955a)
- Changed: ⚡ optimize history truncation complexity in HistoryManager (59c1e5e)
- Changed: 🔒 Prevent plaintext API key leak on keyring failure (8b1bd8c)
- Changed: Fix linting errors that caused CI to fail (0a27fbb)
- Changed: ⚡ Optimize tight loop in search tools (3120e9a)
- Changed: Merge branch 'main' of <https://github.com/julesklord/mentask> (622c34c)
- Changed: docs: expand README with detailed v0.10.0 modular architecture and security layer (6a86ce9)
- Changed: docs: consolidate changelog and update wiki for v0.10.0 (0f9d20b)
- Changed: 🌍 chore: translate system instructions and UI strings to English (68a7b43)
- Changed: 🚀 release: v0.10.0 - modular refactor and CD automation (9ab8fbb)
- Changed: ⚙️ refactor(agent): modularize agent logic into specialized managers (ef65cf2)
- Changed: 📦 chore: refactor core infrastructure and file tools security (d799df4)
- Changed: Merge pull request #78 from julesklord/ux-toast-context-clear-1874985583130748259 (114fb1e)
- Changed: 🎨 Palette: Add toast notification when clearing context (1328d4e)
- Changed: 🎨 Palette: Add toast notification when clearing context (43b67e8)
- Changed: Update README.md (8ffbd20)
- Changed: Update python-ci.yml (f37331c)
- Changed: Update README.md (65a93ef)
- Changed: Update README.md (44cd0f2)
- Changed: Merge pull request #73 from julesklord/palette/localize-dashboard-strings-6118603084491207756 (208f28c)
- Changed: Merge branch 'main' into palette/localize-dashboard-strings-6118603084491207756 (b31c67a)
- Changed: Merge pull request #74 from julesklord/palette/add-input-tooltip-17992643460676732985 (547028c)
- Changed: 🎨 Palette: Add localized tooltip to main prompt input (9cb03e7)
- Changed: 🎨 Palette: [Localize Dashboard UI Strings] (264ac9a)
- Changed: Merge pull request #72 from julesklord/jules-1416051861149424731-f2b7683a (8ea7242)
- Changed: Disable input widget during slash commands and record learning (7b907aa)
- Changed: .gitignore updated (8dcb689)
- Changed: Merge pull request #71 from julesklord/palette-ux-localize-placeholder-11959462695577841809 (c7e965f)
- Changed: 🎨 Palette: Update input placeholder to use localized loading states (bf5b340)
- Changed: Merge pull request #70 from julesklord/palette-ux-input-loading-state-17746392598409794666 (05b1d7e)
- Changed: Merge pull request #69 from julesklord/palette-preserve-error-state-16034395384767057562 (b732439)
- Changed: 🎨 Palette: Preserve mascot visual error state after operations (80350a3)
- Changed: 🎨 Palette: [Preserve Error State]\n\nFix a TUI micro-UX issue where error visual feedback was prematurely cleared. (5735d7f)
- Changed: refactor: restructure tools tests to match src directory (f6a7f55)
- Changed: Merge pull request #61 from julesklord/refactor/tests-core (6dde3f9)
- Changed: Merge pull request #60 from julesklord/refactor/tests-cli (4bd1897)
- Changed: Merge pull request #59 from julesklord/refactor/tests-agent (1298f5a)
- Changed: Merge pull request #58 from julesklord/refactor/move-docs (a9660f2)
- Changed: Merge pull request #57 from julesklord/refactor/move-scripts (49f15f6)
- Changed: Merge pull request #63 from julesklord/docs/add-changes-md (e8ebe61)

### Fixed

- Fixed: test: implement comprehensive integrity suite for workspaces and security (e487dda)
- Fixed: security: implement path escape protection and trust management system (17bc4d8)
- Fixed: Merge pull request #81 from julesklord/jules-security-fix-config-keyring-15356368552684113763 (1aba075)
- Fixed: Merge branch 'main' into jules-security-fix-config-keyring-15356368552684113763 (e19cbbd)
- Fixed: Merge pull request #83 from julesklord/fix-history-path-traversal-6913222568345985593 (19335e7)
- Fixed: Merge pull request #79 from julesklord/alert-autofix-5 (861e369)
- Fixed: Potential fix for code scanning alert no. 5: Workflow does not contain permissions (7df735b)
- Fixed: 🧪 test: implement reliable unit test suite for agent core and security (d109407)
- Fixed: Merge pull request #77 from julesklord/alert-autofix-4 (c6acc71)
- Fixed: Potential fix for code scanning alert no. 4: Workflow does not contain permissions (49faf0f)
- Fixed: Merge pull request #76 from julesklord/alert-autofix-3 (d9bf697)
- Fixed: Potential fix for code scanning alert no. 3: Workflow does not contain permissions (23801ca)
- Fixed: Merge pull request #75 from julesklord/alert-autofix-1 (23daca8)
- Fixed: Potential fix for code scanning alert no. 1: Workflow does not contain permissions (681648b)
- Fixed: 🎨 Palette: Add localized tooltip to main prompt input and fix CI tests (86efba9)
- Fixed: 🎨 Palette: Add localized tooltip to main prompt input and fix CI tests (9cc64c2)
- Fixed: ci: enhance security with gitleaks, dependabot and professional audit (040389d)
- Fixed: Merge pull request #68 from julesklord/ux-error-state-fix-6319414668591106183 (713d130)
- Fixed: Merge branch 'main' into ux-error-state-fix-6319414668591106183 (2005bce)
- Fixed: fix: restore synchronous get_history calls and update tests (3c88626)
- Fixed: fix: restore synchronous chat session creation and update tests (1b81e0d)
- Fixed: fix: resolve async chat creation and update tests (4b08b07)
- Fixed: fix: restore missing _summarize_context definition (d4c2b01)

### Added

- Added: feat: implement dynamic local workspace detection and path isolation (e4f2305)
- Added: feat: refactor core architecture with AgentOrchestrator and hyper-context awareness (7bd4b2a)
- Added: 🎨 feat(ui): push-layout dashboard and TUI adapters (0529617)
- Added: feat: add SECURITY.md and Python CI workflow (103e992)
- Added: feat(ui): add visual loading state to chat input field placeholder (b864af1)
