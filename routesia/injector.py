"""
routesia/injector.py - Injector for plugins
"""

import inspect

from routesia.plugin import PluginManager


class Provider:
    pass


class Injector:
    def __init__(self, plugin_manager=PluginManager, static_providers={}):
        self.plugin_manager = plugin_manager
        # Assign the given static providers
        self.providers = static_providers.copy()
        # Load static providers from plugins
        for plugin in self.plugin_manager.plugins.values():
            for provider in plugin.static_providers:
                if provider not in self.providers:
                    self.providers[provider] = self.run(provider)

    def get_provider(self, cls):
        "Get an instance for a provider"
        if cls not in self.providers and issubclass(cls, Provider):
            self.providers[cls] = self.run(cls)
        return self.providers[cls]

    def run(self, fn, **kwargs):
        """Run fn with context and providers. If an argument is provided via
        kwargs, it will be passed to the function, otherwise, the type
        annotation for the function argument is used to look up a provider.
        """
        if inspect.isclass(fn):
            items = fn.__init__.__annotations__.items()
        else:
            items = fn.__annotations__.items()
        for arg, cls in items:
            kwargs[arg] = self.get_provider(cls)
        return fn(**kwargs)
