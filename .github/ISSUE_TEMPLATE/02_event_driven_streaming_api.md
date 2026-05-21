---
name: "2. Event-Driven Streaming and API Decoupling"
about: "Decouple ChatAgent from the CLI console renderer to support external clients (VS Code, Web UI, etc.)."
title: "[Architecture] Decouple ChatAgent CLI from Core to Support Multi-Client Event Streaming"
labels: ["enhancement", "architecture"]
assignees: []
---

## Summary
The current `ChatAgent` is tightly coupled to the CLI `CliRenderer` and `console` outputs. To make `mentask` a universal AI agent capable of running behind VS Code extensions, web interfaces, or Slack bots, we must decouple the core agent logic and expose a clean, structured event-streaming API.

## Proposed Architecture
- Refactor the streaming generator in `AgentOrchestrator` and `ChatAgent` to yield structured, typed Pydantic event models (e.g., `ThoughtEvent`, `TextChunkEvent`, `ToolCallEvent`, `ToolResultEvent`, `StatusEvent`).
- Extract all console UI formatting and rendering logic from `ChatAgent` and `AgentOrchestrator` into a dedicated `TerminalClient` subscriber.

## Technical Tasks
- [ ] Define standard Pydantic models for all agent events in `mentask/agent/schema.py`.
- [ ] Refactor `ChatAgent._stream_response` to yield these structured events instead of interacting with the renderer.
- [ ] Implement an event dispatcher in `ChatAgent` to support multiple listener registration.
- [ ] Create a prototype FastAPI or WebSocket API server (`mentask/api/`) that exposes this event stream.
- [ ] Update CLI/TUI logic to act as a pure consumer of the new decoupled event stream.
