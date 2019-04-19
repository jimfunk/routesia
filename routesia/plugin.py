"""
routesia/plugin.py - Plugin handler
"""

import importlib
import inspect
import pkgutil


class Plugin:
    static_providers = []
    "Providers that should be loaded on startup"


class PluginManager:
    def __init__(self):
        self.plugin_modules = {}
        self.plugins = {}

    def load_plugin_module(self, name: str):
        "Load plugin module by it's full name"
        module = importlib.import_module(name)
        self.plugin_modules[name] = module

    def load_all_plugin_modules(self):
        "Load all installed plugin modules"
        for finder, name, ispkg in pkgutil.iter_modules():
            if name.startswith('routesia_'):
                self.load_plugin_module(name)

    def load_plugins(self):
        "Load all plugins found in plugin modules"
        for plugin_module in self.plugin_modules.values():
            for class_name, obj in inspect.getmembers(plugin_module):
                if inspect.isclass(obj) and issubclass(obj, Plugin):
                    self.plugins[class_name] = obj()
