from selectors import DefaultSelector, EVENT_READ
import pytest

from routesia.eventqueue import EventQueue


def test_put():
    queue = EventQueue()
    queue.put("foo")
    assert "foo" in queue.dq


def test_get():
    queue = EventQueue()
    queue.put("foo")
    item = queue.get()
    assert item == "foo"
    assert len(queue.dq) == 0


def test_get_empty():
    queue = EventQueue()

    with pytest.raises(BlockingIOError):
        queue.get()


def test_select_empty():
    queue = EventQueue()
    selector = DefaultSelector()
    selector.register(queue, EVENT_READ)

    events = selector.select(timeout=0.01)

    assert len(events) == 0


def test_select_non_empty():
    queue = EventQueue()
    selector = DefaultSelector()
    selector.register(queue, EVENT_READ)

    queue.put("foo")

    events = selector.select(timeout=0.01)

    assert len(events) == 1
    key, _ = events[0]
    assert key.fd == queue.fileno()


def test_multiple_items():
    queue = EventQueue()
    selector = DefaultSelector()
    selector.register(queue, EVENT_READ)

    queue.put("foo")
    queue.put("bar")

    events = selector.select(timeout=0.01)
    assert len(events) == 1

    item = queue.get()
    assert item == "foo"

    events = selector.select(timeout=0.01)
    assert len(events) == 1

    item = queue.get()
    assert item == "bar"

    events = selector.select(timeout=0.01)
    assert len(events) == 0
