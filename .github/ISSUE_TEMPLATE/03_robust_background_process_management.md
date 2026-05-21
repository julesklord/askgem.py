---
name: "3. Robust Background Process and LSP Lifecycle Management"
about: "Improve daemon/process tracking and LSP client connection resilience."
title: "[Stability] Implement Resilient Background Process and LSP Lifecycle Management"
labels: ["stability", "bug"]
assignees: []
---

## Summary
The agent spawns background processes such as the Ruff LSP server, shell command daemons, and other external subprocesses. If the CLI session crashes, is forcibly closed, or is interrupted (e.g., via `Ctrl+C` during tool execution), these background processes can become orphans or zombies, consuming memory and locking file handles.

## Proposed Architecture
Enhance `ProcessTracker` and `LSPClient` to implement strict process lifecycle management, connection heartbeats, and reliable shutdown hooks.

## Technical Tasks
- [ ] Add system signal handlers (`SIGINT`, `SIGTERM`, `SIGHUP`) in CLI startup to trigger clean process shutdowns.
- [ ] Implement an active heartbeat mechanism in `LSPClient` to auto-detect crashed or unresponsive LSP servers.
- [ ] Improve `ProcessTracker` to periodically sweep and kill orphaned child processes spawned by tools.
- [ ] Ensure that `LSPClient.stop()` is guaranteed to close stdin/stdout/stderr pipes and terminate/kill the sub-process cleanly under all circumstances.
- [ ] Write robustness tests that simulate tool crashes or session terminations to verify no processes are leaked.
