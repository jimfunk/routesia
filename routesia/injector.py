"""
routesia/injector.py - Injector for plugins
"""

from collections import OrderedDict
import inspect

from routesia.exceptions import InvalidProvider


class Provider:
    def startup(self):
        pass

    def shutdown(self):
        pass


class Injector(Provider):
    def __init__(self):
        self.providers = OrderedDict()
        self.add_provider(Injector, self)

    def add_provider(self, cls, instance):
        if not isinstance(instance, Provider):
            raise InvalidProvider
        self.providers[cls] = instance

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

    def startup(self):
        for provider in self.providers.values():
            if provider != self:
                provider.startup()

    def shutdown(self):
        for provider in self.providers.values():
            if provider != self:
                provider.shutdown()
