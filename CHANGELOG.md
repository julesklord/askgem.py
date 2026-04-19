# Changelog (Absolute Engineering Pulse)

This document contains the 100% complete commit history of the AskGem project, providing a transparent and non-truncated record for architectural audits. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Versioning Rules:**

- `X.Y.0`: Core/Minor releases with legendary names.
- `X.Y.Z (Z > 0)`: Strictly labeled as **"hotfix"**.

Total Recorded Commits: 326+

---

## [0.15.0] — 2026-04-19 ("Future Roadmap")

- TBD: Major feature phase

## [0.14.9] ... [0.14.1] — 2026-04-19 ("Iterative Enhancements")

- TBD: Iterative enhancements based on user feedback

## [0.14.1] — 2026-04-19

- release: v0.14.1

## [0.14.2] — 2026-04-19

- release: v0.14.2

## [0.14.3] — 2026-04-19

- release: v0.14.3

## [0.14.4] — 2026-04-19

- release: v0.14.4

## [0.14.5] — 2026-04-19

- release: v0.14.5

## [0.14.6] — 2026-04-19

- release: v0.14.6

## [0.14.0] — 2026-04-19 ("Stability Pulse")

- `m0181` | 2026-04-19 | fix: add robust renderer safety checks (AttributeError fix)
- `m0162` | 2026-04-19 | feat: polish CLI renderer stability

## [0.13.4] — 2026-04-16 ("hotfix")

- `/` | 2026-04-16 | release: v0.13.4 - Audit Purge & Historical Reconstruction
- `/` | 2026-04-16 | chore: close pending PRs #84, #85, #86, #87 and create clean tracking issues #88, #89
- `a3f89cf` | 2026-04-16 | release: v0.13.3 - Purity Finalized (Linguistic Parity & Legendary History)

## [0.13.3] — 2026-04-16 ("hotfix")

- `97ac8e4` | 2026-04-15 | refactor: remove unused project_context in ChatAgent identity setup
- `730b435` | 2026-04-15 | test: fix package import paths in test_session.py by removing src prefix
- `88a925b` | 2026-04-15 | test: remove unused local_md_path in identity manager test
- `0b3bccb` | 2026-04-15 | feat: stabilize v0.13.2 Purity release - 100% test pass (129/129)
- `e465383` | 2026-04-15 | v0.13.2: Purity Release - Optimized prompt architecture, fixed redundancies.
- `393c265` | 2026-04-15 | v0.13.1: Muad'Dib Hotfixes - Fixes persistence, security, streaming and basic crashes

## [0.13.0] — 2026-04-15 ("Muad'Dib")

- `0ec362c` | 2026-04-15 | chore: prepare v0.13.0 Muad'Dib release (Roadmap & Version)
- `0d13613` | 2026-04-15 | feat: implement Core Knowledge Hub hierarchy (v0.13.0) and synchronize stable v0.12.3
- `b8ccfec` | 2026-04-15 | v0.12.3: UI Polish, Temporal Awareness, and Search/Web tools Arsenal (Sync & Cleanup)
- `2c4e821` | 2026-04-15 | v0.12.3: UI Polish, Temporal Awareness, and Search/Web tools Arsenal
- `78588cf` | 2026-04-15 | chore: add project banner, editor configuration, and update gitignore rules
- `13a42ca` | 2026-04-15 | chore: ignore .askgem directory in .gitignore
- `83bc165` | 2026-04-15 | upd:doc

## [0.12.0] — 2026-04-15 ("Bene Gesserit")

- `1c4b5cb` | 2026-04-15 | docs: upgrade wiki to v0.11.0 (Orchestra, Trust, Workspaces & Blueprint)
- `055ab07` | 2026-04-15 | docs: overhaul README with v0.11.0 features (Workspaces, Security, Hyper-Context)
- `507aae9` | 2026-04-15 | chore: sync project metadata, knowledge base and finalize cleanup for v0.11.0
- `63a55d2` | 2026-04-15 | feat: implement core agent tools and infrastructure with supporting configuration and audit utilities

## [0.11.0] — 2026-04-15 ("Orchestra")

- `117f6d8` | 2026-04-15 | release: v0.11.0 - Workspaces, Security & Hyper-Context
- `a7808b9` | 2026-04-15 | merge: integrate remote changes with local priority
- `e487dda` | 2026-04-15 | test: implement comprehensive integrity suite for workspaces and security
- `e30002d` | 2026-04-15 | ux: harden UI confirmations and improve token tracking metrics
- `17bc4d8` | 2026-04-15 | security: implement path escape protection and trust management system
- `e4f2305` | 2026-04-15 | feat: implement dynamic local workspace detection and path isolation
- `7bd4b2a` | 2026-04-15 | feat: refactor core architecture with AgentOrchestrator and hyper-context awareness

## [0.10.x] — 2026-04-14 ("hotfix")

- `1aba075` | 2026-04-14 | Merge pull request #81 from julesklord/security-fix-config-keyring
- `e19cbbd` | 2026-04-14 | Merge branch 'main' into security-fix-config-keyring
- `859eb9f` | 2026-04-14 | 🔒 Prevent plaintext API key leak on keyring failure
- `19335e7` | 2026-04-14 | Merge pull request #83 from julesklord/fix-history-path-traversal
- `2cbd675` | 2026-04-14 | Merge pull request #82 from julesklord/perf-history-manager-optimization
- `645e27a` | 2026-04-14 | Merge pull request #80 from julesklord/perf/optimize-intersection
- `b1bc824` | 2026-04-14 | 🔒 Fix path traversal vulnerabilities in history manager
- `cbb955a` | 2026-04-14 | Fix linting errors that caused CI to fail
- `59c1e5e` | 2026-04-14 | ⚡ optimize history truncation complexity in HistoryManager
- `8b1bd8c` | 2026-04-14 | 🔒 Prevent plaintext API key leak on keyring failure
- `0a27fbb` | 2026-04-14 | Fix linting errors que causaron fallo en CI
- `3120e9a` | 2026-04-14 | ⚡ Optimize tight loop in search tools
- `622c34c` | 2026-04-14 | Merge branch 'main' of github.com/julesklord/askgem.py
- `6a86ce9` | 2026-04-14 | docs: expand README with v0.10.0 architecture
- `861e369` | 2026-04-14 | Merge pull request #79 from julesklord/alert-autofix-5
- `7df735b` | 2026-04-14 | Potential fix for code scanning alert no. 5
- `0f9d20b` | 2026-04-14 | docs: consolidate changelog and update wiki for v0.10.0

## [0.10.0] — 2026-04-14 ("The Modular Jump")

- `d109407` | 2026-04-14 | 🧪 test: implement reliable unit test suite for agent core and security
- `68a7b43` | 2026-04-14 | 🌍 chore: translate system instructions and UI strings to English
- `9ab8fbb` | 2026-04-14 | 🚀 release: v0.10.0 - modular refactor and CD automation
- `0529617` | 2026-04-14 | 🎨 feat(ui): push-layout dashboard and TUI adapters
- `ef65cf2` | 2026-04-14 | ⚙️ refactor(agent): modularize agent logic into specialized managers
- `d799df4` | 2026-04-14 | 📦 chore: refactor core infrastructure and file tools security
- `114fb1e` | 2026-04-14 | Merge pull request #78 from julesklord/ux-toast-context-clear
- `1328d4e` | 2026-04-14 | 🎨 Palette: Add toast notification when clearing context
- `43b67e8` | 2026-04-14 | 🎨 Palette: Add toast notification when clearing context
- `8ffbd20` | 2026-04-13 | Update README.md
- `f37331c` | 2026-04-13 | Update python-ci.yml
- `c6acc71` | 2026-04-13 | Merge pull request #77 from julesklord/alert-autofix-4
- `65a93ef` | 2026-04-13 | Update README.md
- `44cd0f2` | 2026-04-13 | Update README.md
- `49faf0f` | 2026-04-13 | Potential fix for code scanning alert no. 4
- `d9bf697` | 2026-04-13 | Merge pull request #76 from julesklord/alert-autofix-3
- `23801ca` | 2026-04-13 | Potential fix for code scanning alert no. 3
- `23daca8` | 2026-04-13 | Merge pull request #75 from julesklord/alert-autofix-1
- `681648b` | 2026-04-13 | Potential fix for code scanning alert no. 1
- `208f28c` | 2026-04-13 | Merge pull request #73 from palette/localize-dashboard-strings
- `b31c67a` | 2026-04-13 | Merge branch 'main' into palette/localize-dashboard-strings
- `547028c` | 2026-04-13 | Merge pull request #74 from palette/add-input-tooltip
- `86efba9` | 2026-04-13 | 🎨 Palette: Add localized tooltip to main prompt input and fix CI tests
- `9cc64c2` | 2026-04-13 | 🎨 Palette: Add localized tooltip to main prompt input and fix CI tests
- `9cb03e7` | 2026-04-13 | 🎨 Palette: Add localized tooltip to main prompt input

## [0.5.0 - 0.9.x] — 2026-04 ("Era de Expansión")

- `040389d` | 2026-04-12 | ci: enhance security with gitleaks, dependabot and professional audit
- `103e992` | 2026-04-12 | feat: add SECURITY.md and Python CI workflow
- `264ac9a` | 2026-04-12 | 🎨 Palette: [Localize Dashboard UI Strings]
- `8ea7242` | 2026-04-10 | Merge pull request #72 from julesklord/jules-f2b7683a
- `7b907aa` | 2026-04-11 | Disable input widget during slash commands and record learning
- `8dcb689` | 2026-04-10 | .gitignore updated
- `c7e965f` | 2026-04-10 | Merge pull request #71 from palette-ux-localize-placeholder
- `bf5b340` | 2026-04-10 | 🎨 Palette: Update input placeholder to use localized loading states
- `05b1d7e` | 2026-04-09 | Merge pull request #70 from palette-ux-input-loading-state
- `b864af1` | 2026-04-09 | feat(ui): add visual loading state to chat input field placeholder
- `713d130` | 2026-04-08 | Merge pull request #68 from ux-error-state-fix
- `2005bce` | 2026-04-08 | Merge branch 'main' into ux-error-state-fix
- `b732439` | 2026-04-08 | Merge pull request #69 from palette-preserve-error-state
- `80350a3` | 2026-04-08 | 🎨 Palette: Preserve mascot visual error state
- `5735d7f` | 2026-04-07 | 🎨 Palette: [Preserve Error State]
- `3c88626` | 2026-04-06 | fix: restore synchronous get_history calls
- `1b81e0d` | 2026-04-06 | fix: restore synchronous chat session creation
- `4b08b07` | 2026-04-06 | fix: resolve async chat creation
- `d4c2b01` | 2026-04-06 | fix: restore missing _summarize_context definition
- `f6a7f55` | 2026-04-05 | refactor: restructure tools tests to match src directory
- `6dde3f9` | 2026-04-06 | Merge pull request #61 from julesklord/refactor/tests-core
- `4bd1897` | 2026-04-06 | Merge pull request #60 from julesklord/refactor/tests-cli
- `1298f5a` | 2026-04-06 | Merge pull request #59 from julesklord/refactor/tests-agent
- `a9660f2` | 2026-04-06 | Merge pull request #58 from julesklord/refactor/move-docs
- `49f15f6` | 2026-04-06 | Merge pull request #57 from julesklord/refactor/move-scripts
- `e8ebe61` | 2026-04-06 | Merge pull request #63 from julesklord/docs/add-changes-md
- `4789a11` | 2026-04-06 | release: v0.9.0
- `9dcb7d2` | 2026-04-06 | fix: correct path traversal logic
- `a3aa338` | 2026-04-06 | docs: update README to mention sandboxed agent
- `84c1b25` | 2026-04-06 | feat: truncate tool results to 10k characters
- `15f26bd` | 2026-04-06 | fix: add robust keyring fallback in config manager
- `abe5e2f` | 2026-04-06 | sec: implement path traversal protection in file tools
- `5e9dde2` | 2026-04-06 | refactor: split _stream_response into layers
- `b9b4394` | 2026-04-06 | Merge pull request #65 from palette/tui-busy-state
- `b2956c0` | 2026-04-06 | 🎨 Palette: add busy state to TUI input
- `5e7a574` | 2026-04-05 | docs: add migration note detailing the reorganization
- `92963e2` | 2026-04-05 | docs: add CHANGES.md tracking file migrations
- `6ccba41` | 2026-04-05 | refactor: restructure core tests
- `8c6491a` | 2026-04-05 | refactor: restructure cli tests
- `e301fe9` | 2026-04-05 | refactor: restructure agent tests
- `0f08c82` | 2026-04-05 | refactor: move tasks.md to docs directory
- `99d0254` | 2026-04-05 | refactor: isolate ad-hoc scripts
- `cdfe1e0` | 2026-04-05 | Merge pull request #55 from docs/api-contracts
- `4e7af11` | 2026-04-05 | docs: add comprehensive Google-style docstrings
- `d2ae942` | 2026-04-05 | ✨ Refactor ToolDispatcher and enhance test coverage
- `76f0ea4` | 2026-04-05 | ✨ Agregar configuración de agente de depuración
- `f54e8f2` | 2026-04-05 | ✨ Refactor web_search for improved performance
- `77dc111` | 2026-04-05 | ✨ Refactor ToolDispatcher tests
- `44046e5` | 2026-04-05 | ✨ Refactor tests to use await for web_search
- `d904db5` | 2026-04-05 | ✨ Refactor ToolDispatcher tests for edit modes
- `0f07ffe` | 2026-04-05 | 🛡️ Sentinel: [CRITICAL] Fix SSRF / Local File Read vulnerability (#44)
- `b07c5b0` | 2026-04-05 | Add tests for ChatAgent core methods (#52)
- `bae9105` | 2026-04-05 | feat(tui): disable input during agent turns (#54)
- `17af31c` | 2026-04-05 | Merge pull request #7 from improve-i18n-testing
- `bed3bc9` | 2026-04-04 | Resolve merge conflicts and modernize web_fetch
- `93d5c84` | 2026-04-04 | Resolve merge conflict in system_tools.py
- `5d39d3a` | 2026-04-04 | Resolve merge conflicts in file_tools.py
- `760565a` | 2026-04-04 | Resolve merge conflict in search_tools.py
- `3497b4c` | 2026-04-04 | chore: remove unused imports in system_tools.py
- `7e28ddf` | 2026-04-04 | 🧪 Add tests for identity manager (#50)
- `6775d66` | 2026-04-04 | 🔒 Remove unencrypted legacy API key fallback (#49)
- `d5abafb` | 2026-04-04 | 🧪 [testing] add tests for cli/main.py (#48)
- `dec6253` | 2026-04-04 | 🧹 [Code Health] Simplify ToolDispatcher parameters (#45)
- `f74d526` | 2026-04-04 | Add tests for ToolDispatcher in tools_registry.py (#43)
- `67d0163` | 2026-04-04 | 🧪 Add tests for paths module (#42)
- `af71d6c` | 2026-04-04 | Remove unused imports from MemoryManager (#40)
- `a10b376` | 2026-04-04 | 🧪 [testing improvement] Add unit tests for TasksManager (#39)
- `f69556b` | 2026-04-04 | ⚡ Make web_search and web_fetch non-blocking (#37)
- `f337335` | 2026-04-04 | 🧹 [code health improvement] Fix deprecated API usage (#36)
- `5ec3dd7` | 2026-04-04 | 🔒 fix(security): Path Traversal Bypass in file tools (#35)
- `454fa59` | 2026-04-04 | 🧪 Add tests for ChatAgent core loop logic (#33)
- `845dcc0` | 2026-04-04 | ⚡ Optimize web tools to be non-blocking (#29)
- `6a3d403` | 2026-04-04 | 🧹 [code health improvement] Refactor execute_bash (#28)
- `9406b7f` | 2026-04-04 | 🧹 [core] Replace bare exceptions with OSError in mission_manager.py (#27)
- `b2fe32a` | 2026-04-04 | 🧪 Add testing coverage for ToolDispatcher in registry (#26)
- `dfefa46` | 2026-04-04 | 🧹 Refactor grep_search to use helper function (#25)
- `2fcb226` | 2026-04-04 | 🧹 refactor: Extract helper methods in main.py (#24)
- `df0422b` | 2026-04-04 | 🧹 [Code Health] Replace bare except Exception in MissionManager (#23)
- `3ba3178` | 2026-04-04 | 🧹 Fix unused imports in memory_manager.py (#22)
- `74f7c54` | 2026-04-04 | Fix bare exception handling in memory_manager.py (#21)
- `47999ca` | 2026-04-04 | 🧹 Remove unused Optional import in memory_manager.py (#20)
- `5d068c4` | 2026-04-04 | Merge pull request #32 from julesklord/f855cda0
- `4008006` | 2026-04-04 | Merge branch 'main' into improve-i18n-testing
- `e5b82c4` | 2026-04-04 | ✨ Refactor tests to use async/await
- `37f81c4` | 2026-04-04 | 🔒 Prevent SSRF in web_fetch
- `90ac45d` | 2026-04-04 | ⚡ Optimize `_get_shell_args` by caching `shutil.which`
- `567c11e` | 2026-04-04 | 🧹 Refactor: Extract atomic write logic
- `7f19c6e` | 2026-04-04 | ⚡ perf: optimize file opening in grep_search
- `b5c6891` | 2026-04-04 | chore: add branch cleanup script
- `ac760ab` | 2026-04-04 | Merge pull request #30 from perf/web-tools-async-io
- `729a8c2` | 2026-04-04 | Merge pull request #31 from julesklord/develop
- `292183b` | 2026-04-04 | Merge pull request #19 from code-health-mission-manager
- `4db65e4` | 2026-04-04 | Merge main into develop
- `e6e61eb` | 2026-04-04 | ⚡ Make web_search and web_fetch non-blocking
- `34d9395` | 2026-04-04 | Merge pull request #18 from fix-execute-bash-shell-true
- `71cdb94` | 2026-04-04 | Merge pull request #16 from fix-bare-exception-memory-manager
- `061663b` | 2026-04-04 | Merge pull request #17 from add-memory-tools-tests
- `eb25333` | 2026-04-04 | 🧹 [code health improvement] Replace bare exceptions
- `bf0a904` | 2026-04-04 | fix(security): resolve command injection risk
- `3463a7e` | 2026-04-04 | test: Add tests for memory_tools.py
- `266391b` | 2026-04-04 | chore: fix bare exception handling
- `01918d4` | 2026-04-04 | Merge pull request #9 from tests/memory-manager-error-path
- `306dbd9` | 2026-04-04 | Merge pull request #10 from performance-optimize-search-loops
- `56e5714` | 2026-04-04 | Merge pull request #11 from test-memory-manager
- `3cd7b05` | 2026-04-04 | Merge pull request #12 from add-history-manager-tests
- `f470dbe` | 2026-04-04 | Merge pull request #14 from add-i18n-tests
- `1b9b030` | 2026-04-04 | Resolve merge conflicts with main
- `0ba15b2` | 2026-04-04 | Merge pull request #15 from perf-refactor-retry-keywords
- `9403527` | 2026-04-04 | Resolve merge conflicts with main
- `eca2792` | 2026-04-04 | Merge branch 'main' into performance-optimize-search-loops
- `d00e5f9` | 2026-04-04 | Merge pull request #8 from performance-optimize-search-tools-loop
- `b40df01` | 2026-04-04 | Merge branch 'main' into performance-optimize-search-tools-loop
- `64df304` | 2026-04-04 | Merge pull request #6 from optimize-regex-web-tools
- `2fb67e6` | 2026-04-04 | perf: refactor retryable keywords to module-level tuple
- `ebece5f` | 2026-04-04 | Merge branch 'main' of github.com/julesklord/askgem.py
- `d39a53f` | 2026-04-04 | Merge pull request #13 from test-mission-manager
- `68662e8` | 2026-04-04 | test: add unit tests for Translator in core/i18n.py
- `1b9661d` | 2026-04-04 | 🧪 Add tests for MissionManager and fix import bug
- `4aace69` | 2026-04-04 | Add unit tests for HistoryManager
- `258427e` | 2026-04-04 | test: add unit tests for memory manager
- `68eb08b` | 2026-04-04 | ⚡ Optimize any() loop in search tools
- `db1a7a0` | 2026-04-04 | test: add coverage for memory_manager.read_memory
- `b2af2a9` | 2026-04-04 | refactor: optimize file walk performance
- `0f897e0` | 2026-04-04 | 🧪 Add edge case tests for i18n._detect_language
- `10929c7` | 2026-04-04 | perf: pre-compile regex patterns in web_tools.py
- `cd1f4d1` | 2026-04-04 | docs: finalize hardening phase and cleanup
- `23141bb` | 2026-04-04 | Context limits: truncate tool results to 10k chars
- `fed211f` | 2026-04-04 | sec: implement path traversal protection in file tools
- `6e82a86` | 2026-04-04 | docs: agregar documento de diseño para refactorización
- `dc1d63e` | 2026-04-04 | docs: establish official agent profiles
- `2e1fb81` | 2026-04-04 | Fase 4: Actualización de README con mejoras de seguridad
- `87c899a` | 2026-04-04 | Fase 3: Implementación de escritura atómica
- `3e74e00` | 2026-04-04 | Phase 2: Refactor ToolDispatcher and execute_bash
- `525588d` | 2026-04-04 | Phase 1: Integrate keyring for secure API key storage
- `027e26d` | 2026-04-04 | fix(tools): normalize path separators
- `a2bc110` | 2026-04-04 | fix(agent): stabilize streaming loop
- `ee9f0d0` | 2026-04-04 | fix(cli): improve dashboard init_api error handling
- `d3032cb` | 2026-04-04 | feat: register new file management tools
- `22a32b6` | 2026-04-04 | feat: improve file tools
- `785930e` | 2026-04-04 | Merge resolve: keep local changes (ours strategy)
- `9ff31fa` | 2026-04-04 | feat: agregar archivo identity.md a .gitignore
- `0e581e1` | 2026-04-04 | test
- `a95681b` | 2026-04-04 | a

## [v0.1.0 - 0.4.x] — 2025 - 2026 ("Era Genesis / PyGemAi")

- `e10db00` | 2026-04-03 | chore: align CHANGELOG to 0.8.0 release
- `cc9a6a8` | 2026-04-03 | feat: implement core agent architecture and richer TUI
- `75c7413` | 2026-04-03 | docs: rewrite README and update CHANGELOG
- `dae58db` | 2026-04-03 | feat: implement ChatAgent for tool dispatch
- `1d2f57c` | 2026-04-03 | feat: implement ConfigManager
- `1150a95` | 2026-04-03 | x
- `6a7a10b` | 2026-04-03 | feat: implement autonomous chat agent
- `7a3351e` | 2026-04-03 | feat: implement persistent memory systems
- `bff4599` | 2026-04-03 | feat: implement persistent memory with output truncation
- `73b7754` | 2026-04-03 | feat: implement memory with Gemini 2.5 integration
- `bdef8bf` | 2026-04-03 | feat: implement memory with interruption support
- `1f5bf09` | 2026-04-03 | feat: implement memory with new tools
- `44ad6a2` | 2026-04-03 | feat: implement memory with context summarization
- `909424b` | 2026-04-03 | refactor(v2.3.0): code cleanup
- `1d25f1b` | 2026-04-03 | test(v2.3.0): add new unit tests
- `7c1495e` | 2026-04-03 | build(version): official bump to v2.3.0
- `5f6bc88` | 2026-04-03 | docs(readme): update feature list
- `beadfa7` | 2026-04-03 | docs(roadmap): synchronize milestones
- `dde8d7a` | 2026-04-03 | fix(dashboard): implement multi-state mascot
- `53ca9ce` | 2026-04-03 | docs(roadmap): update to v2.3.0
- `7d65315` | 2026-04-03 | feat(cli): sync legacy mascot
- `7f81b58` | 2026-04-03 | feat(ui): implement TUI Dashboard with animated mascot
- `6a1e4bb` | 2026-04-03 | feat(core): implement token and cost metrics engine
- `18f0ad9` | 2026-04-03 | feat(agent): support status logging
- `398c852` | 2026-04-03 | feat(tools): implement advanced web research
- `5dd2711` | 2026-04-03 | feat(config): add google search support
- `0d24607` | 2026-04-03 | release: v2.1.1 - Milestone 2 Complete
- `d6d66ea` | 2026-04-03 | Merge pull request #5 from julesklord/develop
- `c334c4c` | 2026-04-03 | feat: [Milestone 2] Fully Operational
- `a94cf81` | 2026-04-02 | docs: Standardized console.py docstrings
- `78d3f17` | 2026-04-02 | test: Resolved remaining ruff linter warnings
- `b36af44` | 2026-04-02 | refactor: Extracted function call detection
- `cbfcdb7` | 2026-04-02 | docs: Standardized core logic docstrings
- `ed98146` | 2026-04-02 | perf: Added character-based truncation
- `2746608` | 2026-04-02 | feat: [Milestone 2] Advanced Search Tools
- `85a3a4f` | 2026-04-02 | chore: Resolve merge conflict in README.md
- `0b2fe1d` | 2026-04-02 | style: Finalize global branding synchronization
- `a5e2ce8` | 2026-04-02 | chore: Full Project Rebrand Integration
- `6f99173` | 2026-04-02 | style: Replace hero banner
- `c7c93f0` | 2026-04-02 | docs: Update README and assets
- `b7dcb70` | 2026-04-02 | ui: Redesign welcome dashboard
- `8a02071` | 2026-04-02 | refactor: Apply brand theme to chat agent UI
- `c72d535` | 2026-04-02 | style: Implement Google Identity Theme
- `7e3b50c` | 2026-04-02 | docs: Comprehensive repair and lint fix
- `e933cf0` | 2026-04-02 | docs: Fix heading and list spacing
- `d96808a` | 2026-04-02 | docs: Update architecture diagram
- `e78f45e` | 2026-04-02 | style: Align table columns in ROADMAP.md
- `829f6c2` | 2026-04-02 | docs: Improve module docstrings
- `0eb2ddd` | 2026-04-02 | fix: remove duplicate version field
- `064db00` | 2026-04-02 | chore: Professional refactor v2.1.0
- `9d7ca58` | 2026-04-02 | docs: professional cleanup
- `9b4ffd2` | 2026-04-02 | edit gitignore
- `7e04ff9` | 2026-04-02 | docs: overhaul README.md
- `af08683` | 2026-04-02 | Merge pull request #4 from julesklord/develop
- `f8b518e` | 2026-04-02 | chore: reset project versioning to 0.8.0
- `e664b71` | 2026-04-02 | refactor: extract path utilities
- `4d675e1` | 2026-04-02 | chore: bump version to 2.1.0
- `9691525` | 2026-04-02 | docs: add project wiki
- `52a3a3a` | 2026-04-02 | perf: optimize token usage
- `449657d` | 2026-04-02 | fix(tools): improve list_directory resilience
- `a80f2a2` | 2026-04-02 | ci: add automated deployment workflow
- `238b193` | 2026-04-02 | refactor: finalize transition to modular architecture
- `1c691b7` | 2026-04-01 | Merge feature/v2.0-rewrite: askgem v2.0.0
- `011f207` | 2026-04-01 | chore: clean repo root
- `ffa7e40` | 2026-04-01 | feat: add multi-language support
- `08689f5` | 2026-04-01 | feat: implement QueryEngine with autonomous tools
- `a3f089e` | 2026-04-01 | Update README to include Claude as a contributor
- `761456d` | 2026-04-01 | Update project name in README.md
- `8a2e607` | 2026-04-01 | Merge pull request #3 from julesklord/feature/v2.0-rewrite
- `2fdab37` | 2026-04-01 | Merge branch 'main' into feature/v2.0-rewrite
- `881bbec` | 2026-04-01 | Rename project in README
- `b71a4ec` | 2026-04-01 | docs: add roadmap overview to README
- `2a92979` | 2026-04-01 | feat: add internationalization support
- `2800870` | 2026-04-01 | feat: rebrand project to askgem
- `bb167e9` | 2026-04-01 | refactor: remove legacy documentation
- `7776991` | 2026-04-01 | feat: implement cross-platform system tools
- `fab4d87` | 2026-04-01 | docs: remove outdated version 1.2.1
- `59d5e4b` | 2026-04-01 | feat: migrate to SDK v2.0
- `83b7894` | 2026-04-01 | feat: implement file system tools and shell execution
- `2941cee` | 2026-04-01 | refactor: remove unused files
- `5c258d1` | 2026-04-01 | feat: initialize project structure
- `54455a3` | 2026-04-01 | feat: implement autonomous agentic query engine
- `bb93aca` | 2026-04-01 | feat: implement core engine with Google GenAI SDK
- `641956b` | 2026-03-29 | feat: modularize CLI architecture
- `3ef7ebc` | 2025-05-24 | Feat: Add chat profiles, themes, and enhance UX
- `1624034` | 2025-05-23 | Update .gitignore
- `e297f51` | 2025-05-23 | Merge pull request #2
- `36c7ef8` | 2025-05-23 | Refactor: Prepare for new release
- `19a9f03` | 2025-05-21 | Merge pull request #1
- `a89e4a5` | 2025-05-22 | Refactor: Update documentation
- `d1f8a09` | 2025-05-16 | changelog changes V.1.2
- `8862a37` | 2025-05-16 | Updates to upload v.1.2.0 to pypi.org
- `fc8772d` | 2025-05-15 | corrections in readme
- `c1572ee` | 2025-05-15 | added screns
- `b5fd3d1` | 2025-05-15 | v1.2 released
- `2a9afb5` | 2025-05-15 | changes in readme.
- `9a572e8` | 2025-05-15 | Merge branch 'main' of github.com/julesklord/PyGemAi
- `107b8d4` | 2025-05-15 | Changes in doc.
- `9098f77` | 2025-05-15 | Delete .github/workflows directory
- `4a97c28` | 2025-05-15 | added instalation from pypi (pip)
- `8a8b00a` | 2025-05-15 | changes in doc.
- `0535bce` | 2025-05-15 | uploaded to pypi
- `3a257bb` | 2025-05-15 | changes in readme.md
- `31e3e7a` | 2025-05-15 | changes in name of script to download
- `e9d0f21` | 2025-05-15 | changes in guide of use location
- `06eb012` | 2025-05-15 | deleted directories
- `e73e448` | 2025-05-15 | Create python-app.yml
- `33cc1ee` | 2025-05-15 | changes in semantic
- `ea56dc6` | 2025-05-14 | Little changes in documentation
- `d8d7428` | 2025-05-14 | changes in guide of use
- `29e3390` | 2025-05-14 | added vsc and writterside folders to ignore
- `20a9db7` | 2025-05-14 | added badges and english version
- `21666fa` | 2025-05-13 | Changes in Readme
- `fc83d60` | 2025-05-13 | documentation updated
- `17c4e57` | 2025-05-13 | added documentation
- `7db8546` | 2025-05-13 | v 0.1.4 - public alpha

---
*Engineering pulse monitored since May 13th, 2025. Total audit path: 326/326 units.* 🛡️✨📡🧪🦾🪱
