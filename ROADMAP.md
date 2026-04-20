# askgem — Development Roadmap

> **Last Updated:** April 20, 2026
> **Current Version:** `0.16.3`
> **Maintainer:** [@julesklord](https://github.com/julesklord)
> **Status:** Active stabilization / Planning v0.17.0

This document outlines the engineering roadmap for `askgem`, organized into prioritized milestones. The current focus is tightening reliability, documentation coherence, and language-aware editing on top of the existing autonomous core.

---

## Current State Assessment

### What askgem v0.16.2 Can Do Today

| Capability | Status | Description |
| :--- | :--- | :--- |
| **Multimodal Reasoning** | ✅ Shipped | Processes images, audio, and video via base64 encoding. |
| **On-Demand Knowledge** | ✅ Shipped | Optimized Knowledge Hub via `query_knowledge` tool. |
| **Autonomous Orchestration** | ✅ Shipped | Advanced Think -> Act -> Observe loop with 429 retry logic. |
| **TrustManager Security** | ✅ Shipped | Recursive directory validation and Path Traversal prevention. |
| **Web Research** | ✅ Shipped | Live internet search (Google/DDG) and content extraction. |
| **Full Validation** | ✅ Shipped | Broad unit/integration coverage across the core agent, tools, and CLI. |
| **Autonomous LSP** | ✅ Shipped | Real-time verification and self-correction via Ruff LSP. |
| **Professional TUI** | ✅ Shipped | Rich-based streaming CLI with Smuffle/Snuggles themes. |

### Architecture Diagram

```mermaid
graph TD
    A[main.py CLI Entry] --> B[AgentOrchestrator]
    B --> C[SessionManager]
    B --> D[ContextManager]
    B --> E[ToolRegistry]
    E --> F[FileTools]
    E --> G[SystemTools]
    E --> H[WebTools]
    C --> I[MemoryManager]
    C --> J[TokenTracker]
```

---

## Milestone 1: Visual Identity and Stability (COMPLETED)
- [x] API Error Retry with Exponential Backoff
- [x] Dedicated `write_file` Tool
- [x] `/undo` Command (Restores `.bkp` snapshots)
- [x] Graceful Truncation of Oversized Context

## Milestone 2: Code Search Navigation (COMPLETED)
- [x] `grep_search` Tool (Pattern matching)
- [x] `glob_find` Tool (File discovery)
- [x] `diff_file` Tool (Unified diff previews)

## Milestone 3: Web Research Integration (COMPLETED)
- [x] `web_search` Tool (Google Search API integration)
- [x] `web_fetch` Tool (Markdown-friendly content extraction)

## Milestone 4: Architectural Sovereignty (COMPLETED)
- [x] Transition from Monolith to Specialized Managers
- [x] Pydantic integration for Agentturn schemas
- [x] Hierarchical Knowledge Hub (Standard/Global/Local)

---

## Milestone 5: Language Intelligence ("Bene Gesserit") (COMPLETED)

**Theme:** Transition from blind code editing to language-aware engineering.

### 5.1 LSP Client Bridge
- [x] Integration with Ruff via JSON-RPC.
- [x] Automated Lint-Fix Loop (Agent detects diagnostic and self-corrects).

### 5.2 Context Optimization
- [x] Semantic Truncation and proactive summarization.

---

## Milestone 6: Scalable Memory & Intelligence ("Shai-Hulud")

**Priority:** 🔴 High
**Estimated Effort:** Q2 2026
**Theme:** Transition to vector-based memory, deep code understanding, and autonomous engineering.

### 6.1 Vector Memory Integration
- [ ] Implement local RAG (Retrieval-Augmented Generation) for codebase indexing.
- [ ] Persistent project-level embeddings.

### 6.2 Multi-Agent Orchestration
- [ ] Sub-agent spawning for parallel task execution.

### 6.3 Deep Static Analysis & Refactoring
- [ ] Syntax-aware navigation (identifying classes, methods, and dependencies without full file reads).
- [ ] Intelligent Refactoring (safe renaming, method extraction, and dependency management).

### 6.4 Advanced Git Workflow
- [ ] Autonomous commit message generation based on diff analysis.
- [ ] Assisted conflict resolution and branch management.

---

## Milestone 7: Professional Reliability ("Lisan al-Gaib")

**Priority:** 🟡 Medium
**Theme:** Self-testing, deep debugging, and predictive assistance.

### 7.1 Autonomous Testing & TDD
- [ ] Automated unit test generation for new/modified code.
- [ ] Verification-first editing (generating tests before applying changes).

### 7.2 Debugging Intelligence
- [ ] Automated Traceback analysis and root cause identification.
- [ ] Contextual fix suggestions for CLI/Command failures.

---

## Technical Debt & Maintenance

| Item | Priority | Status |
| :--- | :--- | :--- |
| **Translation Parity** | High | ✅ Solved in v0.13.2 (8 locales synchronized). |
| **Docs Consistency** | High | In progress; remove stale dashboard/TUI references and align docs with runtime behavior. |
| **CLI Contract Tests** | High | In progress; entrypoint tests aligned with current `--list` and default startup flow. |
| **Type Hinting** | Low | Partially complete; move toward stricter typing in orchestration and tool layers. |

---

## Version Release Timeline

```text
2026-04-19  v0.15.0  ████████  Kwisatz Haderach: LSP integration
2026-04-20  v0.16.0  ████████  The Golden Path: Professional Consolidation
2026-04-20  v0.16.3  ████████  Stabilization & Branding (CURRENT)
2026-05     v0.17.0  ░░░       Shai-Hulud: Vector Memory & Deep Analysis
2026-06     v0.18.0  ░░░       Lisan al-Gaib: Autonomous Testing & Debugging
```

---
*The code must be stable before the feature set expands.*
