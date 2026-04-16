# Architecture

The system operate across three tightly decoupled layers enforcing strong logical boundaries. As of version **0.13.0**, the system has evolved into an **Orchestrated Hierarchical Architecture**, where a central engine manages cognitive managers, a multi-layered Knowledge Hub, and security centinels.

## High-Level System Diagram

```mermaid
flowchart TD
    CLI(["User execution (askgem)"]) --> Main(cli/main.py)
    Main --> Renderer(cli/renderer.py)
    Renderer <--> Orchestrator(agent/orchestrator.py: AgentOrchestrator)
    
    subgraph Cognitive_Layer [Cognitive Managers]
        Orchestrator --> Session[agent/core/session.py]
        Orchestrator --> Context[agent/core/context.py]
        Orchestrator --> Hub[core/identity_manager.py: KnowledgeManager]
        Orchestrator --> Stream[agent/core/stream.py]
        Orchestrator --> Commands[agent/core/commands.py]
    end

    Hub -. cascada .-> Internal[(Internal Standard Hub)]
    Hub -. cascada .-> UserKB[(Global ~/.askgem)]
    Hub -. cascada .-> LocalKB[(Local .askgem)]

    Orchestrator <--> GenAI[Google Gemini API]
    
    subgraph Security_Layer [Security & Trust Centinel]
        GenAI -. function calls .-> Trust[core/trust_manager.py]
        Trust --> SecurityCheck[core/security.py]
        SecurityCheck --> Tools(tools/)
    end

    Tools --> localDisk[(Local Workspace)]
    Context -. Blueprint .-> localDisk
    Orchestrator --> History(core/history_manager.py)
    History --> Paths(core/paths.py)
    Paths --> localDisk
```

## Module Breakdown

1. **`src/askgem/cli/` (Presentation Layer)**
    * `main.py`: Entry point for session orchestration and environment boot.
    * `renderer.py`: Advanced TUI renderer handling interactive prompts, boxed messages, and streaming Markdown.

2. **`src/askgem/agent/` (Orchestration Layer)**
    * `orchestrator.py`: **[The Heart]** Central loop managing the *Thinking -> Action -> Observation* cycle. Supports simulation playback and tool routing.
    * **`agent/core/` (Cognitive Managers)**
        * `session.py`: Handles API lifecycle, exponential backoff, and simulation injection.
        * `context.py`: **[Blueprint Aware]** Performs project scans and assembles system prompts.
        * `stream.py`: Low-level tool extraction and metrics tracking.

3. **`src/askgem/core/` (State & Safety Layer)**
    * `identity_manager.py`: **[v0.13.0 Knowledge Hub]** Orchestrates the hierarchical training system (Standard -> Global -> Project).
    * `trust_manager.py`: Whitelist management for authorized directories.
    * `security.py`: Real-time risk analysis and path resolution guards.
    * `paths.py`: Maps package-internal folders, local `.askgem/` designs, and global configuration.
    * `metrics.py`: Token consumption and cost tracking.

## Execution Flow (v0.13.0 Hierarchical)

1. **Environmental Boot**: `cli/main.py` detects if the CWD is a Workspace.
2. **Knowledge Aggregation**: `KnowledgeManager` loads the Hub in cascade (internals files, then `~/.askgem`, then local project rules).
3. **Project Blueprint**: `ContextManager` performs a recursive scan of the project tree.
4. **Thinking Phase**: Gemini reasons using the aggregated Knowledge Hub and the injected project context.
5. **Action Request**: If a tool is requested, `TrustManager` and `SecurityCheck` verify the operation.
6. **Persistence**: History, Memory, and Session Metrics are saved within the hierarchical configuration paths.

## Key Design Decisions

* **Hierarchical Intelligence**: Behavioral logic and personality are modular markdown files. No rules are hardcoded in the engine.
* **Proactive Discovery**: The agent is instructed via the Standard Knowledge Hub to use `glob` and `grep` proactively to explore environments.
* **Multimodal Guidelines**: Dedicated standard modules guide the model on how to process images, video, and audio technical data.
