"""
tests/test_injector.py
"""

from routesia.injector import Provider, Injector


class FooProvider(Provider):
    pass


class BarProvider(Provider):
    pass


class DependentLoadfProvider(Provider):
    def __init__(self):
        self.foo = None
        self.baer = None

    def load(self, foo: FooProvider, bar: BarProvider):
        self.foo = foo
        self.bar = bar


def test_load():
    injector = Injector()
    injector.add_provider(FooProvider, FooProvider())
    injector.add_provider(BarProvider, BarProvider())
    injector.load()
    assert isinstance(injector.get_provider(FooProvider), FooProvider)
    assert isinstance(injector.get_provider(BarProvider), BarProvider)


def test_dependent_load():
    injector = Injector()
    injector.add_provider(DependentLoadfProvider, DependentLoadfProvider())
    injector.add_provider(FooProvider, FooProvider())
    injector.add_provider(BarProvider, BarProvider())
    injector.load()
    provider = injector.get_provider(DependentLoadfProvider)
    assert isinstance(provider.foo, FooProvider)
    assert isinstance(provider.bar, BarProvider)


def test_run():
    injector = Injector()
    injector.add_provider(FooProvider, FooProvider())

    def fn(foo: FooProvider):
        assert isinstance(foo, FooProvider)
        return True

    assert injector.run(fn)
