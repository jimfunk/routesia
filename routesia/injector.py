"""
routesia/injector.py - Injector for plugins
"""

from collections import OrderedDict
import inspect

from routesia.exceptions import InvalidProvider, ProviderLoadError


class Provider:
    def __init__(self):
        pass

    def load(self):
        pass

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
        """
        Run fn with context and providers. If an argument is provided via
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

    def load(self):
        """
        Load provider. Mainly used to initialise configuration before startup.
        If a provider defines any provider annotations, its load will occur
        after those providers have been loaded.
        """
        loaded = []
        waiting = list(self.providers.values())
        waiting.remove(self)
        while waiting:
            len_waiting = len(waiting)
            for provider in waiting:
                loadable = True
                for required_class in provider.__init__.__annotations__.values():
                    if required_class not in loaded:
                        loadable = False
                        break
                if loadable:
                    self.run(provider.load)
                    loaded.append(provider.__class__)
                    waiting.remove(provider)
            if len_waiting == len(waiting):
                raise ProviderLoadError("Some providers cannot be loaded due to missing prerequisites: %s" % ', '.join([p.__class__.__name__ for p in waiting]))

    def startup(self):
        for provider in self.providers.values():
            if provider != self:
                self.run(provider.startup)

    def shutdown(self):
        for provider in self.providers.values():
            if provider != self:
                self.run(provider.shutdown)
