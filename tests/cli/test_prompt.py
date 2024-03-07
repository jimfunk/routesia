import pytest

from routesia.cli.ansi import ansi
from routesia.cli.completion import Completion
from routesia.cli.prompt import CompletionSelector, Prompt


def test_selector_empty_fragment():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "",
    )
    assert selector.fragment == ""
    assert selector.matching_completions == [
        Completion("one", "one"),
        Completion("two", "two"),
        Completion("three", "three"),
    ]
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_selector_empty_fragment_completions():
    selector = CompletionSelector(
        [
            Completion("1", "one"),
            Completion("2", "two"),
            Completion("3", "three"),
        ],
        "",
    )
    assert selector.fragment == ""
    assert selector.matching_completions == [
            Completion("1", "one"),
            Completion("2", "two"),
            Completion("3", "three"),
    ]
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_selector_matching_fragment():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "t",
    )
    assert selector.fragment == "t"
    assert selector.matching_completions == [
        Completion("two", "two"),
        Completion("three", "three"),
    ]
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(1) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_selector_matching_fragment_completions():
    selector = CompletionSelector(
        [
            Completion("one", "1 (one)"),
            Completion("two", "2 (two)"),
            Completion("three", "3 (three)"),
        ],
        "t",
    )
    assert selector.fragment == "t"
    assert selector.matching_completions == [
        Completion("two", "2 (two)"),
        Completion("three", "3 (three)"),
    ]
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(1) + \
        ansi.reverse + " 2 (two)   " + ansi.reset + ansi.down(1) + ansi.left(11) + \
        ansi.reverse + " 3 (three) " + ansi.reset + ansi.down(1) + ansi.left(11) + \
        ansi.restore_cursor


def test_selector_nonmatching_fragment():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "f",
    )
    assert selector.fragment == "f"
    assert selector.matching_completions == []
    assert selector.view() == ""


def test_selector_selection_next():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "",
    )
    assert selector.selection is None

    selector.next()
    assert selector.selection == Completion("one", "one")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.next()
    assert selector.selection == Completion("two", "two")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.next()
    assert selector.selection == Completion("three", "three")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.next()
    assert selector.selection == Completion("one", "one")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_selector_selection_previous():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "",
    )
    assert selector.selection is None

    selector.previous()
    assert selector.selection == Completion("three", "three")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.previous()
    assert selector.selection == Completion("two", "two")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.previous()
    assert selector.selection == Completion("one", "one")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.previous()
    assert selector.selection == Completion("three", "three")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_selector_selection_next_no_completions():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "f",
    )
    assert selector.selection is None
    selector.next()
    assert selector.selection is None


def test_selector_selection_previous_no_completions():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "f",
    )
    assert selector.selection is None
    selector.previous()
    assert selector.selection is None


def test_selector_scroll_next():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "",
        max_visible=2,
    )
    assert selector.selection is None

    selector.next()
    assert selector.selection == Completion("one", "one")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.next()
    assert selector.selection == Completion("two", "two")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.next()
    assert selector.selection == Completion("three", "three")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.next()
    assert selector.selection == Completion("one", "one")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_selector_scroll_previous():
    selector = CompletionSelector(
        [
            "one",
            "two",
            "three",
        ],
        "",
        max_visible=2,
    )
    assert selector.selection is None

    selector.previous()
    assert selector.selection == Completion("three", "three")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.previous()
    assert selector.selection == Completion("two", "two")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.previous()
    assert selector.selection == Completion("one", "one")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        " one   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.reverse + "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor

    selector.previous()
    assert selector.selection == Completion("three", "three")
    assert selector.view() == \
        ansi.save_cursor + ansi.down(1) + ansi.left(0) + \
        ansi.reverse + "+two   " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        " three " + ansi.reset + ansi.down(1) + ansi.left(7) + \
        ansi.restore_cursor


def test_prompt_init(stdout):
    Prompt(stdout=stdout)

    assert stdout.value == "> "
    assert stdout.dirty == False


def test_prompt_display_message(stdout):
    prompt = Prompt(stdout=stdout)
    prompt.display_message("foo bar")

    # Since this is always in response to an enter, the cursor will already be
    # on the next line when we display the message
    assert stdout.value == "> foo bar\r\n"
    assert stdout.dirty == False


async def test_prompt_enter(stdout):
    prompt = Prompt(stdout=stdout)

    assert await prompt.enter() is True


def test_prompt_insert_initial_value(stdout):
    prompt = Prompt(stdout=stdout, input="foo")

    assert prompt.input == "foo"
    assert prompt.position == 3
    assert stdout.value == "> foo"
    assert stdout.dirty is False


@pytest.mark.parametrize(
    "input,position,value,start,end",
    [
        ("", 0, "", 0, 0),
        (" ", 0, "", 0, 0),
        ("a", 0, "a", 0, 1),
        ("a", 1, "a", 0, 1),
        (" a", 0, "", 0, 0),
        ("foo", 1, "foo", 0, 3),
        ("foo ", 4, "", 4, 4),
        ("foo  bar", 4, "", 4, 4),
        ("foo bar", 3, "foo", 0, 3),
        ("foo bar", 4, "bar", 4, 7),
        ("foo bar", 5, "bar", 4, 7),
        ("foo bar baz", 7, "bar", 4, 7),
        ("foo bar baz", 8, "baz", 8, 11),
    ]
)
def test_get_current_fragment(stdout, input, position, value, start, end):
    prompt = Prompt(stdout=stdout, input=input)
    prompt.position = position
    fragment = prompt.get_current_fragment()
    assert fragment.value == value
    assert fragment.start == start
    assert fragment.end == end


@pytest.mark.parametrize(
    "input,position,fragments",
    [
        ("", 0, []),
        ("a", 1, []),
        ("a ", 2, ["a"]),
        ("foo", 3, []),
        ("foo ", 4, ["foo"]),
        ("foo bar", 3, []),
        ("foo bar", 4, ["foo"]),
        ("foo bar baz", 7, ["foo"]),
        ("foo bar baz", 8, ["foo", "bar"]),
        ("foo bar baz", 11, ["foo", "bar"]),
        ("foo bar baz ", 12, ["foo", "bar", "baz"]),
    ]
)
def test_get_fragments_before_cursor(stdout, input, position, fragments):
    prompt = Prompt(stdout=stdout, input=input)
    prompt.position = position
    assert prompt.get_fragments_before_cursor() == fragments


def test_prompt_cursor_left(stdout):
    prompt = Prompt(stdout=stdout, input="foo")

    prompt.cursor_left()
    assert prompt.position == 2

    prompt.cursor_left()
    assert prompt.position == 1

    prompt.cursor_left()
    assert prompt.position == 0

    prompt.cursor_left()
    assert prompt.position == 0

    # Cursor only moved 3 times
    assert stdout.value == "> foo" + ansi.left(1) * 3
    assert stdout.dirty is False


def test_prompt_cursor_right(stdout):
    prompt = Prompt(stdout=stdout, input="foo")

    prompt.cursor_left()
    prompt.cursor_left()
    prompt.cursor_left()
    stdout.clear()

    assert prompt.position == 0

    prompt.cursor_right()
    assert prompt.position == 1

    prompt.cursor_right()
    assert prompt.position == 2

    prompt.cursor_right()
    assert prompt.position == 3

    prompt.cursor_right()
    assert prompt.position == 3

    # Cursor only moved 3 times
    assert stdout.value == ansi.right(1) * 3


def test_prompt_cursor_home(stdout):
    prompt = Prompt(stdout=stdout, input="foo")

    prompt.cursor_home()
    assert prompt.position == 0

    assert stdout.value == "> foo" + ansi.left(3)
    assert stdout.dirty is False

    prompt.cursor_home()
    assert prompt.position == 0


def test_prompt_cursor_end(stdout):
    prompt = Prompt(stdout=stdout, input="foo")

    prompt.cursor_left()
    prompt.cursor_left()

    prompt.cursor_end()
    assert prompt.position == 3

    assert stdout.value == "> foo" + ansi.left(1) * 2 + ansi.right(2)
    assert stdout.dirty is False

    prompt.cursor_end()
    assert prompt.position == 3
    assert stdout.value == "> foo" + ansi.left(1) * 2 + ansi.right(2)


def test_prompt_replace_input_empty(stdout):
    prompt = Prompt(stdout=stdout, input="")

    prompt.replace_input("something")

    assert prompt.position == 9
    assert stdout.value == "> " + "something"
    assert stdout.dirty is False


def test_prompt_replace_input_larger(stdout):
    prompt = Prompt(stdout=stdout, input="foo")

    prompt.replace_input("something")

    assert prompt.position == 9
    assert stdout.value == "> foo" + ansi.left(3) + "something"
    assert stdout.dirty is False


def test_prompt_replace_input_smaller(stdout):
    prompt = Prompt(stdout=stdout, input="something")

    prompt.replace_input("foo")

    assert prompt.position == 3
    assert stdout.value == "> something" + ansi.left(9) + "foo" + ansi.save_cursor + "      " + ansi.restore_cursor
    assert stdout.dirty is False


def test_prompt_insert_append(stdout):
    prompt = Prompt(stdout=stdout)

    prompt.insert("a")
    assert prompt.input == "a"
    assert prompt.position == 1

    prompt.insert("b")
    assert prompt.input == "ab"
    assert prompt.position == 2

    prompt.insert(" ")
    assert prompt.input == "ab "
    assert prompt.position == 3

    prompt.insert("c")
    assert prompt.input == "ab c"
    assert prompt.position == 4

    assert stdout.value == "> ab c"
    assert stdout.dirty is False


def test_prompt_insert_prepend(stdout):
    prompt = Prompt(stdout=stdout, input="bar")
    prompt.cursor_left()
    prompt.cursor_left()
    prompt.cursor_left()
    stdout.clear()

    prompt.insert("f")
    assert prompt.input == "fbar"
    assert prompt.position == 1

    prompt.insert("o")
    assert prompt.input == "fobar"
    assert prompt.position == 2

    prompt.insert("o")
    assert prompt.input == "foobar"
    assert prompt.position == 3

    prompt.insert(" ")
    assert prompt.input == "foo bar"
    assert prompt.position == 4

    assert stdout.value == \
        "f" + ansi.save_cursor + "bar" + ansi.restore_cursor + \
        "o" + ansi.save_cursor + "bar" + ansi.restore_cursor + \
        "o" + ansi.save_cursor + "bar" + ansi.restore_cursor + \
        " " + ansi.save_cursor + "bar" + ansi.restore_cursor
    assert stdout.dirty is False


def test_prompt_delete_left(stdout):
    prompt = Prompt(stdout=stdout, input="abc")

    prompt.delete_left()
    assert prompt.input == "ab"
    assert prompt.position == 2

    prompt.delete_left()
    assert prompt.input == "a"
    assert prompt.position == 1

    prompt.delete_left()
    assert prompt.input == ""
    assert prompt.position == 0

    prompt.delete_left()
    assert prompt.input == ""
    assert prompt.position == 0

    # Only 3 deletes
    assert stdout.value == "> abc" + (ansi.left(1) + ansi.clear_right) * 3
    assert stdout.dirty is False


def test_prompt_delete_left_text_to_right(stdout):
    prompt = Prompt(stdout=stdout, input="abc")

    prompt.cursor_left()
    prompt.cursor_left()
    assert prompt.position == 1

    stdout.clear()

    prompt.delete_left()
    assert prompt.input == "bc"
    assert prompt.position == 0

    prompt.delete_left()
    assert prompt.input == "bc"
    assert prompt.position == 0

    # Only 1 delete
    assert stdout.value == ansi.left(1) + ansi.clear_right + "bc" + ansi.left(2)
    assert stdout.dirty is False


def test_prompt_delete_right(stdout):
    prompt = Prompt(stdout=stdout, input="abc")

    prompt.cursor_left()
    assert prompt.position == 2

    stdout.clear()

    prompt.delete_right()
    assert prompt.input == "ab"
    assert prompt.position == 2

    prompt.delete_right()
    assert prompt.input == "ab"
    assert prompt.position == 2

    # Only clear since there is no remaining text
    assert stdout.value == ansi.clear_right
    assert stdout.dirty is False


def test_prompt_delete_right_text_to_right(stdout):
    prompt = Prompt(stdout=stdout, input="abcd")

    prompt.cursor_left()
    prompt.cursor_left()
    prompt.cursor_left()
    assert prompt.position == 1

    stdout.clear()

    prompt.delete_right()
    assert prompt.input == "acd"
    assert prompt.position == 1

    prompt.delete_right()
    assert prompt.input == "ad"
    assert prompt.position == 1

    assert stdout.value == \
        ansi.clear_right + "cd" + ansi.left(2) + \
        ansi.clear_right + "d" + ansi.left()
    assert stdout.dirty is False


def test_update_fragment_end(stdout):
    prompt = Prompt(stdout=stdout, input="foo b")

    stdout.clear()

    prompt.update_fragment(Completion("bar", "bar"))
    assert prompt.input == "foo bar"
    assert prompt.position == 7

    assert stdout.value == ansi.left(1) + "bar"
    assert stdout.dirty is False


def test_update_fragment_middle(stdout):
    prompt = Prompt(stdout=stdout, input="foo b baz")

    prompt.cursor_left()
    prompt.cursor_left()
    prompt.cursor_left()
    prompt.cursor_left()
    assert prompt.position == 5

    stdout.clear()

    prompt.update_fragment(Completion("bar", "bar"))
    assert prompt.input == "foo bar baz"
    assert prompt.position == 7

    assert stdout.value == ansi.left(1) + "bar baz" + ansi.left(4)
    assert stdout.dirty is False


def test_update_fragment_empty(stdout):
    prompt = Prompt(stdout=stdout, input="foo ")

    stdout.clear()

    prompt.update_fragment(Completion("bar", "bar"))
    assert prompt.input == "foo bar"
    assert prompt.position == 7

    assert stdout.value == "bar"
    assert stdout.dirty is False


class SelectionGetter:
    def __init__(self, *items):
        self.items = items
        self.args = None

    async def get(self, args):
        self.args = args
        return self.items


async def test_complete(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)

    assert getter.args == []
    assert prompt.selector
    assert prompt.selector.selection is None


async def test_complete_next(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    await prompt.complete(getter.get)
    assert prompt.selector.selection == Completion("foo", "foo")
    await prompt.complete(getter.get)
    assert prompt.selector.selection == Completion("bar", "bar")


async def test_complete_single_result(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
    )

    await prompt.complete(getter.get)
    assert prompt.selector is None
    assert prompt.input == "foo"


async def test_complete_partial_single_result(stdout):
    prompt = Prompt(stdout=stdout, input="f")

    getter = SelectionGetter(
        "foo",
    )

    await prompt.complete(getter.get)
    assert prompt.selector is None
    assert prompt.input == "foo"


async def test_complete_partial_no_result(stdout):
    prompt = Prompt(stdout=stdout)
    stdout.clear()

    getter = SelectionGetter()

    await prompt.complete(getter.get)
    assert prompt.selector is None
    assert stdout.value == ansi.bell
    assert stdout.dirty is False


async def test_complete_previous(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.complete_previous()
    assert prompt.selector.selection == Completion("baz", "baz")
    prompt.complete_previous()
    assert prompt.selector.selection == Completion("bar", "bar")


async def test_complete_up(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.up()
    assert prompt.selector.selection == Completion("baz", "baz")
    prompt.up()
    assert prompt.selector.selection == Completion("bar", "bar")


async def test_complete_down(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.down()
    assert prompt.selector.selection == Completion("foo", "foo")
    prompt.down()
    assert prompt.selector.selection == Completion("bar", "bar")


async def test_complete_no_selection_enter(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    result = await prompt.enter()
    assert result is True
    assert prompt.selector is None
    assert prompt.input == ""


async def test_complete_selection_enter(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    await prompt.complete(getter.get)
    result = await prompt.enter()
    assert result is False
    assert prompt.selector is None
    assert prompt.input == "foo"


async def test_complete_no_selection_space(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.insert(" ")
    assert prompt.selector is None
    assert prompt.input == " "


async def test_complete_selection_space(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    await prompt.complete(getter.get)
    prompt.insert(" ")
    assert prompt.selector is None
    assert prompt.input == "foo "


async def test_complete_insert_ambiguous(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.insert("b")
    assert prompt.input == "b"
    assert prompt.selector.matching_completions == [
        Completion("bar", "bar"),
        Completion("baz", "baz"),
    ]

    await prompt.complete(getter.get)
    assert prompt.selector.selection == Completion("bar", "bar")


async def test_complete_insert_unambiguous(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.insert("f")
    assert prompt.input == "f"
    assert prompt.selector.matching_completions == [
        Completion("foo", "foo"),
    ]

    await prompt.complete(getter.get)
    assert prompt.selector is None
    assert prompt.input == "foo"


async def test_complete_insert_impossible(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.insert("c")
    assert prompt.input == "c"
    assert prompt.selector.matching_completions == []

    await prompt.complete(getter.get)
    assert prompt.selector is not None
    assert prompt.input == "c"


async def test_complete_delete_left(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    await prompt.complete(getter.get)
    prompt.insert("b")
    prompt.insert("a")
    prompt.insert("r")
    assert prompt.selector.matching_completions == [
        Completion("bar", "bar"),
    ]

    prompt.delete_left()
    assert prompt.input == "ba"
    assert prompt.selector.matching_completions == [
        Completion("bar", "bar"),
        Completion("baz", "baz"),
    ]


async def test_complete_delete_left_entire_fragment(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    prompt.insert("a")
    prompt.insert(" ")
    prompt.insert("b")
    await prompt.complete(getter.get)
    assert prompt.selector.matching_completions == [
        Completion("bar", "bar"),
        Completion("baz", "baz"),
    ]

    prompt.delete_left()
    prompt.delete_left()
    assert prompt.input == "a"
    assert prompt.selector is None


async def test_complete_cursor_left_outside_fragment(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    prompt.insert("a")
    prompt.insert(" ")
    prompt.insert("b")
    await prompt.complete(getter.get)
    assert prompt.selector.matching_completions == [
        Completion("bar", "bar"),
        Completion("baz", "baz"),
    ]

    prompt.cursor_left()
    prompt.cursor_left()
    assert prompt.selector is None


async def test_complete_cursor_right_outside_fragment(stdout):
    prompt = Prompt(stdout=stdout)

    getter = SelectionGetter(
        "foo",
        "bar",
        "baz"
    )

    prompt.insert("b")
    prompt.insert(" ")
    prompt.insert("c")
    prompt.cursor_left()
    prompt.cursor_left()
    await prompt.complete(getter.get)
    assert prompt.selector.matching_completions == [
        Completion("bar", "bar"),
        Completion("baz", "baz"),
    ]

    prompt.cursor_right()
    assert prompt.selector is None
