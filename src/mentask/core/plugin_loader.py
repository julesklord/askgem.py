"""
Dynamic Plugin Loader for mentask.

This module is responsible for discovering, validating, and loading custom
agent tools (plugins) from the user's workspace or global configuration.
"""

import importlib.util
import inspect
import logging
import sys
from typing import Any

from ..agent.tools.base import BaseTool
from .paths import get_plugins_dir

_logger = logging.getLogger("mentask")

class PluginLoader:
    """Handles the dynamic discovery and loading of external mentask tools."""

    def __init__(self, tool_registry: Any):
        """
        Initializes the loader with a reference to the active ToolRegistry.

        Args:
            tool_registry: The active instance of agent.tools.base.ToolRegistry
        """
        self.registry = tool_registry
        self.plugins_dir = get_plugins_dir()

    def discover_and_load(self) -> int:
        """
        Scans the plugins directory, loads valid Python modules, and registers
        any class inheriting from BaseTool into the ToolRegistry.

        Returns:
            int: The number of plugins successfully loaded.
        """
        if not self.plugins_dir.exists() or not self.plugins_dir.is_dir():
            return 0

        loaded_count = 0
        _logger.info(f"Scanning for dynamic plugins in: {self.plugins_dir}")

        for filepath in self.plugins_dir.glob("*.py"):
            if filepath.name == "__init__.py":
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
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Ensure it's a subclass of BaseTool, but NOT BaseTool itself
                    if issubclass(obj, BaseTool) and obj is not BaseTool:
                        try:
                            # Instantiate the tool
                            tool_instance = obj()
                            # Register it
                            self.registry.register(tool_instance)
                            loaded_count += 1
                            _logger.info(f"Successfully loaded dynamic tool: {tool_instance.name} from {filepath.name}")
                        except Exception as e:
                            _logger.error(f"Failed to instantiate tool class {name} in {filepath.name}: {e}")

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
