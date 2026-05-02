"""
Dynamic Plugin Loader for mentask.

This module is responsible for discovering, validating, and loading custom
agent tools (plugins) from the user's workspace or global configuration.
"""

import ast
import importlib.util
import inspect
import logging
import sys
from typing import Any

from ..agent.tools.base import BaseTool
from .paths import get_global_config_dir, get_plugins_dir

_logger = logging.getLogger("mentask")


class PluginLoader:
    """Handles the dynamic discovery and loading of external mentask tools."""

    def __init__(self, tool_registry: Any, trust_manager: Any = None):
        """
        Initializes the loader with a reference to the active ToolRegistry.

        Args:
            tool_registry: The active instance of agent.tools.base.ToolRegistry
            trust_manager: Optional TrustManager for security verification.
        """
        self.registry = tool_registry
        self.plugins_dir = get_plugins_dir()
        self.trust_manager = trust_manager

    def validate_plugin_ast(self, filepath: Path) -> bool:
        """
        Performs static analysis on the plugin code to ensure it meets requirements.
        Checks for at least one subclass of BaseTool.
        """
        try:
            with open(filepath, encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code)
        except Exception as e:
            _logger.error(f"AST parse error for {filepath.name}: {e}")
            return False

        has_base_tool = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    # Check for BaseTool inheritance
                    if (isinstance(base, ast.Name) and base.id == "BaseTool") or (
                        isinstance(base, ast.Attribute) and base.attr == "BaseTool"
                    ):
                        has_base_tool = True
                        break

            # Blocked imports check (Example: preventing direct use of dangerous modules if needed)
            # if isinstance(node, (ast.Import, ast.ImportFrom)):
            #    ...

        if not has_base_tool:
            _logger.warning(f"Plugin {filepath.name} rejected: No class inheriting from BaseTool found.")
            return False

        return True

    def discover_and_load(self) -> int:
        """
        Scans the plugins directory, loads valid Python modules, and registers
        any class inheriting from BaseTool into the ToolRegistry.

        Returns:
            int: The number of plugins successfully loaded.
        """
        if not self.plugins_dir.exists() or not self.plugins_dir.is_dir():
            return 0

        # Security: Only load from local plugins if the directory is trusted
        if self.trust_manager:
            global_plugins = get_global_config_dir() / "plugins"
            is_global = str(self.plugins_dir).startswith(str(global_plugins))

            if not is_global and not self.trust_manager.is_trusted(str(self.plugins_dir)):
                _logger.error(f"🛑 CRITICAL: Refusing to load plugins from UNTRUSTED directory: {self.plugins_dir}")
                return 0

        loaded_count = 0
        _logger.info(f"Scanning for dynamic plugins in: {self.plugins_dir}")

        for filepath in self.plugins_dir.glob("*.py"):
            if filepath.name == "__init__.py":
                continue

            # AST Validation
            if not self.validate_plugin_ast(filepath):
                continue

            plugin_name = filepath.stem
            module_name = f"mentask_dynamic_plugin_{plugin_name}"

            try:
                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if not spec or not spec.loader:
                    _logger.warning(f"Could not load plugin spec from {filepath.name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Inspect the module for BaseTool subclasses
                found_in_file = 0
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Ensure it's a subclass of BaseTool, but NOT BaseTool itself
                    if issubclass(obj, BaseTool) and obj is not BaseTool:
                        try:
                            # Instantiate the tool
                            tool_instance = obj()
                            # Register it
                            self.registry.register(tool_instance)
                            found_in_file += 1
                            loaded_count += 1
                            _logger.info(f"Successfully loaded dynamic tool: {tool_instance.name} from {filepath.name}")
                        except Exception as e:
                            _logger.error(f"Failed to instantiate tool class {name} in {filepath.name}: {e}")

                if found_in_file == 0:
                    _logger.warning(f"Plugin file {filepath.name} loaded but no BaseTool subclasses were registered.")

            except Exception as e:
                _logger.error(f"Error loading plugin file {filepath.name}: {e}")

        return loaded_count

    def refresh(self) -> int:
        """
        Reloads all plugins from the directory. Useful for hot-reloading
        after the agent creates a new tool.
        """
        _logger.info("Refreshing dynamic plugins...")
        # Note: Depending on the requirements, we might want to unregister old dynamic tools first,
        # but for now, re-registering will just overwrite them in the dict if names match.
        return self.discover_and_load()
