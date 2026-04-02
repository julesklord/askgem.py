# Structural Changes

[NEW] src/askgem/core/paths.py — Centralized configuration and history directory paths to resolve circular import dependencies.
[MOVE] src/askgem/main.py → src/askgem/cli/main.py — Extracted CLI entrypoint from the package root to define the cli tier.
[MOVE] src/askgem/ui/console.py → src/askgem/cli/console.py — Merged global console presentation into the localized cli component.
[DELETE] src/askgem/ui/ — Removed ui directory as presentation layer merged with cli layer.
[MOVE] src/askgem/engine/query_engine.py → src/askgem/agent/chat.py — Renamed engine to agent and query_engine to chat to accurately reflect the autonomous chat agent architecture.
[DELETE] src/askgem/engine/ — Deprecated legacy engine directory naming.
[MODIFY] src/askgem/core/config_manager.py — Updated paths logic and refactored missing docstrings.
[MODIFY] src/askgem/core/history_manager.py — Refactored to import from paths module and injected Google-style docstrings.
[MODIFY] src/askgem/core/i18n.py — Applied structure rules and Google-style docstrings.
[MODIFY] src/askgem/tools/file_tools.py — Added core scope boundary module docstrings.
[MODIFY] src/askgem/tools/system_tools.py — Added core scope boundary module docstrings.
[MODIFY] pyproject.toml — Re-wired CLI entrypoint logic to target new cli/main module.
[MODIFY] tests/test_config_manager.py — Aligned mocks with the centralized core/paths.py strategy.
