import os
import importlib.util
import inspect
from pathlib import Path

from oframe.plugin_interface import OPlugin

class PluginManager:
    def __init__(self, core=None, plugin_dirs=None):
        self.core = core
        self.plugins = {}

        if plugin_dirs is None:
            self.plugin_dirs = [
                os.path.expanduser("~/.oframe/plugins"),
                os.path.join(os.getcwd(), "plugins")
            ]
        else:
            self.plugin_dirs = plugin_dirs

    def load_plugins(self):
        """Discovers and loads all plugins from the configured directories."""
        self.plugins.clear()

        for pdir in self.plugin_dirs:
            if not os.path.isdir(pdir):
                continue

            for filename in os.listdir(pdir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    filepath = os.path.join(pdir, filename)
                    module_name = filename[:-3]

                    try:
                        spec = importlib.util.spec_from_file_location(module_name, filepath)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            for name, obj in inspect.getmembers(module, inspect.isclass):
                                if issubclass(obj, OPlugin) and obj is not OPlugin:
                                    plugin_instance = obj(core=self.core)
                                    self.plugins[name] = plugin_instance
                    except Exception as e:
                        print(f"Failed to load plugin {filename}: {e}")

        return self.plugins

    def get_plugin(self, name):
        """Retrieve a loaded plugin by its class name."""
        return self.plugins.get(name)

    def run_plugin(self, name, *args, **kwargs):
        """Run a loaded plugin by its class name."""
        plugin = self.get_plugin(name)
        if plugin:
            return plugin.run(*args, **kwargs)
        else:
            raise ValueError(f"Plugin '{name}' not found.")
