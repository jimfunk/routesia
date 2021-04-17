"""
tests/test_server.py
"""

from routesia.event import Event
from routesia.injector import Provider
from routesia.server import Server


class FooProvider(Provider):
    pass


class BarProvider(Provider):
    def __init__(self, foo: FooProvider):
        self.foo = foo


def test_start_stop():
    server = Server()
    server.add_provider(FooProvider)
    server.add_provider(BarProvider)
    server.start()
    assert server.running is True
    server.stop()
    assert server.running is False


class FooEvent(Event):
    def __init__(self, foo):
        self.foo = foo


def test_event():
    server = Server()
    events = []

    def fn(ev):
        events.append(ev)

    server.subscribe_event(FooEvent, fn)
    server.publish_event(FooEvent(1))
    server.handle_event(server.eventqueue.get())

    assert events
    assert isinstance(events[0], FooEvent)
    assert events[0].foo == 1
