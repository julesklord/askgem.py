"""
Interactive terminal input shell using prompt_toolkit.

Encapsulates advanced terminal features like key bindings, custom autocomplete,
multiline input support, and history, separating UI input loop concerns from the Agent core.
"""

import logging
from typing import Any

_logger = logging.getLogger("mentask.cli.interactive_shell")

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.patch_stdout import patch_stdout
    HAS_PT = True
except ImportError:
    HAS_PT = False


class InteractiveShell:
    """Encapsulates the prompt_toolkit input session and terminal interactions."""

    def __init__(self, config=None):
        self.config = config
        self.session = None
        self._completer = None
        self._key_bindings = None

        if HAS_PT:
            self._key_bindings = KeyBindings()
            # Initialize the session with standard key bindings
            self.session = PromptSession(key_bindings=self._key_bindings)

    @property
    def has_interactive_features(self) -> bool:
        """Returns True if prompt_toolkit interactive features are available."""
        return HAS_PT and self.session is not None

    def set_completer(self, completer: Any) -> None:
        """Sets the active autocompleter dynamically."""
        self._completer = completer
        if self.session:
            self.session.completer = completer

    async def prompt_user(self, prompt_msg: Any, is_multiline: bool = False) -> str:
        """Prompts the user for interactive input with active completion."""
        if HAS_PT and self.session:
            try:
                # Use patch_stdout to keep printed output flowing cleanly
                with patch_stdout():
                    user_input = await self.session.prompt_async(prompt_msg, multiline=is_multiline)
                    return user_input.strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt() from None
        else:
            # Fallback to standard python input
            try:
                # If prompt_msg is prompt_toolkit's ANSI, it can be printed first
                # In standard fallback, rich prompt is printed by chat.py, so we just do input()
                return input().strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt() from None

    async def update_completer(self, agent: Any) -> Any:
        """Dynamically updates the autocompletion NestedCompleter with all model sources."""
        if not HAS_PT:
            return None

        import asyncio

        from prompt_toolkit.completion import NestedCompleter

        from ..cli import themes
        from ..core.model_discovery import (
            discover_cli_models,
            discover_ollama_models,
            get_installed_cli_binaries,
        )
        from ..core.models_hub import hub

        # 1. Slash commands
        completion_dict: dict[str, Any] = {}
        for cmd in agent.commands.get_all_commands():
            completion_dict[cmd] = None

        # 2. Command sub-options (static)
        completion_dict["/colorscheme"] = {t: None for t in themes.THEMES}
        completion_dict["/mode"] = {"auto": None, "manual": None}
        completion_dict["/multiline"] = {"true": None, "false": None}
        completion_dict["/readonly"] = {"true": None, "false": None}
        completion_dict["/usage"] = {"--reset": None, "-r": None}
        completion_dict["/stream"] = {"transient": None, "continuous": None}
        completion_dict["/thinking"] = {"true": None, "false": None}
        completion_dict["/export"] = {"md": None, "html": None, "txt": None, "json": None}
        completion_dict["/git"] = {"status": None, "diff": None, "log": None}
        completion_dict["/diff"] = None
        completion_dict["/context"] = None
        completion_dict["/retry"] = None
        completion_dict["/config"] = None
        completion_dict["/undo"] = None
        completion_dict["/load"] = None
        completion_dict["/sessions"] = None
        completion_dict["/discover"] = None
        completion_dict["/init"] = None
        completion_dict["/clear"] = None
        completion_dict["/reset"] = None
        completion_dict["/compact"] = None
        completion_dict["/stop"] = None
        completion_dict["/trust"] = None
        completion_dict["/untrust"] = None
        completion_dict["/stats"] = None
        completion_dict["/help"] = None
        completion_dict["/"] = None
        completion_dict["/auth"] = {
            "google": None, "openai": None, "anthropic": None,
            "deepseek": None, "mistral": None, "groq": None,
            "together": None, "perplexity": None,
        }

        # 3. Dynamic prompt styles
        if hasattr(agent, "active_renderer") and hasattr(agent.active_renderer, "prompt_engine"):
            styles = {s: None for s in agent.active_renderer.prompt_engine.STYLES}
            completion_dict["/theme"] = {
                "--style": styles,
                "--nerdfonts": {"on": None, "off": None},
            }

        # 4. Model options — multi-source, structured by prefix
        model_options: dict[str, Any] = {"configure": None}

        try:
            # 4a. Cloud models from models.dev (via hub)
            hub.sync_local(config=agent.config)
            for m_id, m_info in hub._flat_models.items():
                p_id = m_info.get("_provider", {}).get("id", "")
                if agent.local_mode and p_id not in ("ollama", "agent"):
                    continue
                if ":" in m_id:
                    continue  # skip hub-generated scoped dupes; we build our own
                model_options[m_id] = None

            # Add provider-scoped cloud entries (e.g. 'google:gemini-2.5-pro')
            for p_id, p_info in (hub._data_store or {}).items():
                if not isinstance(p_info, dict):
                    continue
                for m_id in p_info.get("models", {}):
                    if not agent.local_mode:
                        model_options[f"{p_id}:{m_id}"] = None
        except Exception:
            _logger.debug("Failed to discover cloud models")

        try:
            # 4b. Ollama local models → 'ollama:<model>'
            ollama_models = await asyncio.to_thread(discover_ollama_models, agent.config)
            for m in ollama_models:
                model_options[f"ollama:{m}"] = None
                model_options[m] = None
        except Exception:
            _logger.debug("Failed to discover Ollama models")

        try:
            # 4c. External CLI binaries → '<binary>:<model>'
            installed_clis = await asyncio.to_thread(get_installed_cli_binaries)
            for cli_key in installed_clis:
                cli_models = await asyncio.to_thread(discover_cli_models, cli_key)
                if cli_models:
                    for m in cli_models:
                        model_options[f"{cli_key}:{m}"] = None
                else:
                    # At minimum expose the CLI itself
                    model_options[cli_key] = None
        except Exception:
            _logger.debug("Failed to discover CLI binary models")

        completion_dict["/model"] = model_options if model_options else {
            "configure": None,
            agent.model_name: None,
        }

        # Build and install the completer
        new_completer = NestedCompleter.from_nested_dict(completion_dict)
        if self._completer:
            self._completer.options = new_completer.options
        else:
            self._completer = new_completer

        if self.session:
            self.session.completer = self._completer

        return self._completer
