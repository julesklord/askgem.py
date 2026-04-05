# Structural Changes Migration Note

The following files are being moved (via independent PRs) to better separate concerns, match the `src/` directory layout, and keep the repository root clean (following Python standard project layout recommendations).

[ACTION] tests/test_chat_agent.py → tests/agent/test_chat_agent.py — Match src/askgem/agent module structure
[ACTION] tests/test_tools_registry.py → tests/agent/test_tools_registry.py — Match src/askgem/agent module structure
[ACTION] tests/test_cli_main.py → tests/cli/test_cli_main.py — Match src/askgem/cli module structure
[ACTION] tests/test_dashboard_smoke.py → tests/cli/test_dashboard_smoke.py — Match src/askgem/cli module structure
[ACTION] tests/test_config_manager.py → tests/core/test_config_manager.py — Match src/askgem/core module structure
[ACTION] tests/test_history_manager.py → tests/core/test_history_manager.py — Match src/askgem/core module structure
[ACTION] tests/test_i18n.py → tests/core/test_i18n.py — Match src/askgem/core module structure
[ACTION] tests/test_identity_manager.py → tests/core/test_identity_manager.py — Match src/askgem/core module structure
[ACTION] tests/test_memory_manager.py → tests/core/test_memory_manager.py — Match src/askgem/core module structure
[ACTION] tests/test_metrics.py → tests/core/test_metrics.py — Match src/askgem/core module structure
[ACTION] tests/test_mission_manager.py → tests/core/test_mission_manager.py — Match src/askgem/core module structure
[ACTION] tests/test_paths.py → tests/core/test_paths.py — Match src/askgem/core module structure
[ACTION] tests/test_tasks_manager.py → tests/core/test_tasks_manager.py — Match src/askgem/core module structure
[ACTION] tests/test_file_tools.py → tests/tools/test_file_tools.py — Match src/askgem/tools module structure
[ACTION] tests/test_memory_tools.py → tests/tools/test_memory_tools.py — Match src/askgem/tools module structure
[ACTION] tests/test_search_tools.py → tests/tools/test_search_tools.py — Match src/askgem/tools module structure
[ACTION] tests/test_security_file_tools.py → tests/tools/test_security_file_tools.py — Match src/askgem/tools module structure
[ACTION] tests/test_system_tools.py → tests/tools/test_system_tools.py — Match src/askgem/tools module structure
[ACTION] tests/test_web_tools.py → tests/tools/test_web_tools.py — Match src/askgem/tools module structure
[ACTION] tests/diagnostic_usability.py → scripts/diagnostic_usability.py — Isolate ad-hoc scripts from test suites
[ACTION] cleanup_branches.sh → scripts/cleanup_branches.sh — Clean up repository root and centralize tooling
[ACTION] tasks.md → docs/tasks.md — Clean up repository root and centralize documentation
