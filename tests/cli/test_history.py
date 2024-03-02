import os
import pytest

from routesia.cli.history import History


@pytest.fixture
def history_filename(tmpdir):
    return os.path.join(tmpdir, "rcl_history")


@pytest.fixture
def history(history_filename):
    return History(filename=history_filename)


def test_init_no_file(history_filename):
    History(filename=history_filename)


def test_add(history):
    history.add("foo bar")
    history.add("spam eggs")

    assert history.items == [
        "foo bar",
        "spam eggs",
    ]


def test_save(history, history_filename):
    history.add("foo bar")
    history.add("spam eggs")
    history.save()

    assert os.path.isfile(history_filename)
    with open(history_filename, "r") as f:
        assert f.readlines() == [
            "foo bar\n",
            "spam eggs",
        ]


def test_load(history, history_filename):
    history.add("foo bar")
    history.add("spam eggs")
    history.save()

    history = History(filename=history_filename)
    assert history.items == [
        "foo bar",
        "spam eggs",
    ]


def test_max_size(history_filename):
    history = History(size=3, filename=history_filename)
    history.add("foo bar")
    history.add("baz qux")
    history.add("spam eggs")
    assert history.items == [
        "foo bar",
        "baz qux",
        "spam eggs",
    ]

    history.add("strawberry tart")

    assert history.items == [
        "baz qux",
        "spam eggs",
        "strawberry tart",
    ]


def test_history_cursor_previous(history):
    history.add("foo bar")
    history.add("baz qux")
    history.add("spam eggs")
    cursor = history.get_cursor()
    assert cursor.previous() == "spam eggs"
    assert cursor.previous() == "baz qux"
    assert cursor.previous() == "foo bar"
    assert cursor.previous() == "foo bar"


def test_history_cursor_next(history):
    history.add("foo bar")
    history.add("baz qux")
    history.add("spam eggs")
    cursor = history.get_cursor()
    assert cursor.previous()
    assert cursor.previous()
    assert cursor.previous() == "foo bar"
    assert cursor.next() == "baz qux"
    assert cursor.next() == "spam eggs"
    assert cursor.next() == ""


def test_history_cursor_previous_empty(history):
    cursor = history.get_cursor()
    assert cursor.previous() == ""


def test_history_cursor_next_empty(history):
    cursor = history.get_cursor()
    assert cursor.next() == ""
