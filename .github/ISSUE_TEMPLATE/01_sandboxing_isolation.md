---
name: "1. Command Sandboxing and Execution Isolation"
about: "Implement a secure isolated environment (e.g., Docker/Firecracker) to run shell commands safely."
title: "[Security] Implement Command Sandboxing and Execution Isolation"
labels: ["enhancement", "security"]
assignees: []
---

## Summary
Currently, `mentask` executes shell commands and file edits directly on the host operating system. To make this agent safe for production, multi-tenant use, or distribution to third parties, all command executions and file manipulations must run within an isolated sandbox environment.

## Proposed Architecture
Introduce a `SandboxManager` abstraction that can interface with different backend providers:
- **Local (Default)**: Direct execution (current behavior, for trusted directories).
- **Docker**: Spawn temporary containers on-demand, mounting the workspace with restricted permissions.
- **Micro-VMs**: Support Firecracker/Fly.io-style lightweight virtual machines for multi-tenant isolation.

## Technical Tasks
- [ ] Create `mentask/core/sandbox.py` with an abstract base class `BaseSandbox`.
- [ ] Implement `DockerSandbox` that pulls a lightweight Python image, mounts the repository, and executes commands inside the container.
- [ ] Refactor `ShellTool` and `PythonReplTool` to delegate command execution to the active sandbox manager.
- [ ] Add configuration settings in `config_manager` to toggle sandboxing modes (`sandbox_mode: "none" | "docker" | "vm"`).
- [ ] Write integration tests verifying that commands run in the sandbox cannot access host files.
