import pytest

from routesia.cli import (
    CommandNode,
    CommandNotFound,
    InvalidCommandDefinition,
    InvalidArgument,
    DuplicateArgument,
)


async def test_add_command(cli):
    async def show_foo():
        pass

    async def show_bar():
        pass

    cli.add_command("show foo", show_foo)
    cli.add_command("show bar", show_bar)

    assert len(cli.router.root_node.children) == 1
    assert "show" in cli.router.root_node.children
    show = cli.router.root_node.children["show"]
    assert isinstance(show, CommandNode)
    assert show.handler is None
    assert len(show.children) == 2

    assert "foo" in show.children
    foo = show.children["foo"]
    assert isinstance(foo, CommandNode)
    assert foo.children == {}
    assert foo.handler == show_foo

    assert "bar" in show.children
    bar = show.children["bar"]
    assert isinstance(bar, CommandNode)
    assert bar.children == {}
    assert bar.handler == show_bar


async def invalid_command_definition(cli):
    calls = []

    async def show_foo(arg1, arg2):
        calls.append((arg1, arg2))

    with pytest.raises(InvalidCommandDefinition):
        cli.add_command("show foo @arg1 :arg2", show_foo)

    with pytest.raises(InvalidCommandDefinition):
        cli.add_command("show foo *arg1 :arg2", show_foo)


async def test_variable_command(cli):
    calls = []

    async def show_foo(arg):
        calls.append(arg)

    cli.add_command("show foo :arg", show_foo)

    await cli.handle_command("show foo value")

    assert calls == ["value"]


async def test_branches_variable_and_non_variable(cli):
    foo_calls = []
    foo_all_calls = []

    async def show_foo(arg):
        foo_calls.append(arg)

    async def show_foo_all():
        foo_all_calls.append(True)

    cli.add_command("show foo :arg", show_foo)
    cli.add_command("show foo all", show_foo_all)

    await cli.handle_command("show foo value")
    assert foo_calls == ["value"]

    await cli.handle_command("show foo all")
    assert foo_all_calls == [True]


async def test_variable_command_multiple_branches(cli):
    foo_bar_calls = []
    foo_baz_calls = []

    async def show_foo_bar(arg):
        foo_bar_calls.append(arg)

    async def show_foo_baz(arg):
        foo_baz_calls.append(arg)

    cli.add_command("show foo :arg bar", show_foo_bar)
    cli.add_command("show foo :arg baz", show_foo_baz)

    await cli.handle_command("show foo value bar")
    assert foo_bar_calls == ["value"]

    await cli.handle_command("show foo value2 baz")
    assert foo_baz_calls == ["value2"]


async def test_variable_subcommands(cli):
    foo_bar_calls = []
    foo_bar_baz_calls = []

    async def show_foo_bar(arg1):
        foo_bar_calls.append(arg1)

    async def show_foo_bar_baz(arg1, arg2):
        foo_bar_baz_calls.append((arg1, arg2))

    cli.add_command("show foo :arg1 bar", show_foo_bar)
    cli.add_command("show foo :arg1 bar :arg2 baz", show_foo_bar_baz)

    await cli.handle_command("show foo value bar")
    assert foo_bar_calls == ["value"]

    await cli.handle_command("show foo value bar value2 baz")
    assert foo_bar_baz_calls == [("value", "value2")]


async def test_keyword_arguments(cli):
    foo_calls = []

    async def show_foo(arg):
        foo_calls.append(arg)

    cli.add_command("show foo @arg", show_foo)

    await cli.handle_command("show foo arg value")
    assert foo_calls == ["value"]


async def test_multiple_keyword_arguments(cli):
    foo_calls = []

    async def show_foo(arg1, arg2):
        foo_calls.append((arg1, arg2))

    cli.add_command("show foo @arg1 @arg2", show_foo)

    await cli.handle_command("show foo arg1 spam arg2 eggs")
    assert foo_calls == [("spam", "eggs")]


async def test_unknown_keyword_argument(cli):
    foo_calls = []

    async def show_foo(arg1, arg2):
        foo_calls.append((arg1, arg2))

    cli.add_command("show foo @arg1 @arg2", show_foo)

    with pytest.raises(InvalidArgument):
        await cli.handle_command("show foo arg1 spam arg3 eggs")


async def test_duplicate_keyword_argument(cli):
    foo_calls = []

    async def show_foo(arg):
        foo_calls.append(arg)

    cli.add_command("show foo @arg", show_foo)

    with pytest.raises(DuplicateArgument):
        await cli.handle_command("show foo arg spam arg eggs")


async def test_list_keyword_arguments(cli):
    foo_calls = []

    async def show_foo(arg):
        foo_calls.append(arg)

    cli.add_command("show foo *arg", show_foo)

    await cli.handle_command("show foo arg spam arg eggs")
    assert foo_calls == [["spam", "eggs"]]


async def test_unknown_command(cli):
    foo_calls = []

    async def show_foo(arg):
        foo_calls.append(arg)

    cli.add_command("show foo :arg", show_foo)

    with pytest.raises(CommandNotFound):
        await cli.handle_command("show bar spam")


async def test_root_completions(cli):
    cli.add_command("show foo", print)
    cli.add_command("set foo", print)
    cli.add_command("delete foo", print)

    assert await cli.router.get_command_completions([]) == [
        "show",
        "set",
        "delete",
    ]


async def test_child_completions(cli):
    cli.add_command("show", print)
    cli.add_command("show foo", print)
    cli.add_command("show bar", print)
    cli.add_command("show baz", print)

    assert await cli.router.get_command_completions(["show"]) == [
        "foo",
        "bar",
        "baz",
    ]


async def test_argument_completions(cli):
    def foo(arg):
        pass

    async def complete_arg(**args):
        return ["spam", "eggs"]

    cli.add_command("show foo :arg", foo)

    cli.add_argument_completer("arg", complete_arg)

    assert await cli.router.get_command_completions(["show", "foo"]) == [
        "spam",
        "eggs",
    ]


async def test_keyword_argument_completions(cli):
    def foo(arg1=None, arg2=None):
        pass

    async def complete_arg1(**args):
        return ["foo", "bar"]

    async def complete_arg2(**args):
        return ["spam", "eggs"]

    cli.add_command("show foo @arg1 @arg2", foo)

    cli.add_argument_completer("arg1", complete_arg1)
    cli.add_argument_completer("arg2", complete_arg2)

    assert sorted(await cli.router.get_command_completions(["show", "foo"])) == [
        "arg1",
        "arg2",
    ]

    assert sorted(await cli.router.get_command_completions(["show", "foo", "arg1"])) == [
        "bar",
        "foo",
    ]

    assert sorted(await cli.router.get_command_completions(["show", "foo", "arg1", "foo"])) == [
        "arg2",
    ]

    assert sorted(await cli.router.get_command_completions(["show", "foo", "arg1", "foo", "arg2"])) == [
        "eggs",
        "spam",
    ]


async def test_argument_completions_no_completer(cli):
    def foo(arg):
        pass

    cli.add_command("show foo :arg", foo)

    assert await cli.router.get_command_completions(["show", "foo"]) == []


async def test_argument_completions_multiple_completers(cli):
    def foo(arg1):
        pass

    def bar(arg2):
        pass

    async def complete_arg1(**args):
        return ["spam", "eggs"]

    async def complete_arg2(**args):
        return ["bar", "baz"]

    cli.add_command("show :arg1 foo", foo)
    cli.add_command("show :arg2 bar", bar)

    cli.add_argument_completer("arg1", complete_arg1)
    cli.add_argument_completer("arg2", complete_arg2)

    assert await cli.router.get_command_completions(["show"]) == [
        "spam",
        "eggs",
        "bar",
        "baz",
    ]


async def test_argument_completions_previous_args(cli):
    def foo(arg1, arg2, arg3):
        pass

    completion_calls = []

    async def complete_arg3(**args):
        completion_calls.append(args)
        return ["spam", "eggs"]

    cli.add_command("show :arg1 :arg2 foo :arg3", foo)

    cli.add_argument_completer("arg3", complete_arg3)

    assert await cli.router.get_command_completions(["show", "one", "two", "foo"]) == [
        "spam",
        "eggs",
    ]

    assert completion_calls == [
        {
            "arg1": "one",
            "arg2": "two",
        },
    ]
