"""
hosteria/cli/__init__.py - CLI appplication
"""

import asyncio
from asyncio import Queue
from collections import OrderedDict
import inspect
import sys
import termios
import tty
import typing
from types import UnionType

from routesia.cli.history import History
from routesia.cli.keyreader import KeyReader, Key
from routesia.cli.prompt import Prompt
from routesia.rpc import RPCInvalidArgument, RPCUnspecifiedError
from routesia.rpcclient import RPCClient
from routesia.service import Provider, ServiceExit


class CommandException(Exception):
    pass


class CommandNotFound(CommandException):
    pass


class InvalidCommandDefinition(CommandException):
    pass


class InvalidArgument(CommandException):
    pass


class DuplicateArgument(CommandException):
    pass


class CommandNode:
    def __init__(self, fragment=None):
        self.fragment = fragment
        self.children = {}
        self.handler = None
        self.keyword_arguments = set()
        self.keyword_list_arguments = set()
        self.disabled_completion_arguments = set()

    def set_handler(self, handler, keyword_arguments=None, keyword_list_arguments=None):
        self.handler = handler
        if keyword_arguments is not None:
            self.keyword_arguments = set()
            for keyword_argument in keyword_arguments:
                arg = keyword_argument.rstrip("!")
                if keyword_argument.endswith("!"):
                    self.disabled_completion_arguments.add(arg)
                self.keyword_arguments.add(arg)

        if keyword_list_arguments is not None:
            self.keyword_list_arguments = set()
            for keyword_argument in keyword_list_arguments:
                arg = keyword_argument.rstrip("!")
                if keyword_argument.endswith("!"):
                    self.disabled_completion_arguments.add(arg)
                self.keyword_list_arguments.add(arg)

    def match(self, fragments: list[str], completion: bool = False) -> tuple["CommandNode", dict[str, str]]:
        """
        Return the child matching the given fragments.

        Returns a tuple of the matched command node and a dict of the parsed
        variable values.
        """
        if not fragments:
            return self, {}

        if fragments[0] in self.children:
            return self.children[fragments[0]].match(fragments[1:], completion=completion)
        else:
            for name, child in self.children.items():
                if name.startswith(":"):
                    node, args = child.match(fragments[1:], completion=completion)
                    if node:
                        args[name[1:].rstrip("!")] = fragments[0]
                        return node, args
            if self.handler:
                # Check the remaining fragments for keyword arguments
                keyword_fragments = fragments[:]
                args = OrderedDict()
                while keyword_fragments:
                    if len(keyword_fragments) < 2:
                        if completion:
                            args[keyword_fragments[0]] = None
                            break
                        else:
                            raise InvalidArgument(keyword_fragments[0])

                    name, value = keyword_fragments[:2]
                    keyword_fragments = keyword_fragments[2:]

                    if name in self.keyword_arguments:
                        if name in args:
                            raise DuplicateArgument(name)
                        args[name] = value
                    elif name in self.keyword_list_arguments:
                        if name in args:
                            args[name].append(value)
                        else:
                            args[name] = [value]
                    else:
                        raise InvalidArgument(name)

                return self, args

        raise CommandNotFound(fragments[0])


class CommandRouter:
    def __init__(self):
        self.root_node = CommandNode()
        self.argument_completers = {}

    def add(self, pattern, handler):
        node = self.root_node
        keyword_arguments = []
        keyword_list_arguments = []

        fragments = pattern.split()
        for i, fragment in enumerate(fragments):
            if fragment.startswith("@") or fragment.startswith("*"):
                # Start of keyword arguments
                for fragment in fragments[i:]:
                    if fragment.startswith("@"):
                        keyword_arguments.append(fragment[1:])
                    elif fragment.startswith("*"):
                        keyword_list_arguments.append(fragment[1:])
                    else:
                        raise InvalidCommandDefinition(
                            f"Positional command fragment '{fragment}' may not be defined after keyword arguments"
                        )
                break

            if fragment in node.children:
                node = node.children[fragment]
            else:
                new_node = CommandNode(fragment)
                node.children[fragment] = new_node
                node = new_node

        node.set_handler(handler, keyword_arguments, keyword_list_arguments)

    def add_argument_completer(self, name: str, completer: callable):
        """
        Add an argument completer
        """
        self.argument_completers[name] = completer

    def get_command_handler(self, command) -> tuple[callable, dict]:
        """
        Get command handler and arguments from input command
        """
        fragments = command.split()

        result, args = self.root_node.match(fragments)

        if not result.handler:
            raise CommandNotFound(command)

        return result.handler, args

    async def get_command_completions(self, fragments: list[str]):
        try:
            node, args = self.root_node.match(fragments, completion=True)
        except CommandNotFound:
            return []

        completions = []
        for child in node.children:
            if child.startswith(":"):
                if not child.endswith("!"):
                    completer = self.argument_completers.get(child[1:])
                    if completer:
                        for child_completion in await completer(**args):
                            completions.append(child_completion)
            else:
                completions.append(child)

        keyword_value = False
        if args:
            last_keyword_arg, last_keyword_value = list(args.items())[-1]
            if not last_keyword_value:
                keyword_value = True
                keyword_completer = self.argument_completers.get(last_keyword_arg)
                if keyword_completer and last_keyword_arg not in node.disabled_completion_arguments:
                    for arg_completion in await keyword_completer(**args):
                        completions.append(arg_completion)

        if not keyword_value:
            for keyword_argument in node.keyword_arguments:
                if keyword_argument not in args:
                    completions.append(keyword_argument.rstrip("!"))

            for keyword_list_argument in node.keyword_list_arguments:
                completions.append(keyword_list_argument.rstrip("!"))

        return completions


class CLI(Provider):
    def __init__(self, rpcclient: RPCClient, stdin=sys.stdin, stdout=sys.stdout, operation_timeout=5):
        super().__init__()
        self.rpcclient = rpcclient
        self.stdin = stdin
        self.stdout = stdout
        self.operation_timeout = operation_timeout

        self.application = None
        self.router = CommandRouter()
        self.key_queue = Queue(maxsize=65535)
        self.history = History()

    def add_command(self, pattern: str, handler: callable):
        """
        Add a command

        The command must be a coroutine.

        The pattern represents the command as typed. For example:

            show foo

        If a component of the pattern starts with ``:``, ``@`` or ``*`` it
        will represent an argument that will be passed to the handler via a
        keyword argument of the name without the prefix. For example, the
        component ``:foo`` will result in the value being passed as the
        ``foo`` argument to the handler.

        If completion is desired, the argument name without the prefix should
        be added using the ``add_argument_completer()`` method. If you have an
        argument you are using for multiple commands but want to exclude
        completion for it in one instance, appeng the ``!`` character to it.

        The ``:`` prefix represents a positional argument. The expected input
        is simply the value. These must always be defined before keyword
        arguments.

        The ``@`` prefix represents a simple keyword argument. The expected
        input is the arguemnt name followed by whitespace, followed by the
        value. Argument order does not matter as long as they are after
        positional arguments.

        The ``*`` prefix represents a repeated keyword argument. The expected
        input is exactly the same a simple keyword argument but may be
        specified multiple times. The value passed to the handler will be a
        list of all given values.

        All variables and arguments will be passed to the handler as keyword
        arguments, even when defined as positional in the pattern.

        If a handler argument is anotated with a type, the argument value will
        be coerced to it before passing it. If no annotation is given, a
        string will be passed. Union types are supported in the case an
        argument can be one of multiple types.

        For example given the pattern:

            show foo :selector @location *tag

        and the command input::

            show foo bar location home tag spam tag eggs

        The handler will be called as::

            handler(
                selector="bar",
                location="home",
                tag=["spam", "eggs"],
            )
        """
        self.router.add(pattern, handler)

    def add_argument_completer(self, name: str, completer: callable):
        """
        Add an argument completer

        The completer must be a callable that returns a list of strings used
        for completion matching.

        If a command has multiple arguments, arguments defined to the left
        will be passed to the completer.
        """
        self.router.add_argument_completer(name, completer)

    async def handle_command(self, cmd):
        command, input_args = self.router.get_command_handler(cmd)
        args = {}
        for name, value in input_args.items():
            args[name.replace("-", "_")] = value

        signature = inspect.Signature.from_callable(command)
        for name, value in args.items():
            if name not in signature.parameters:
                raise InvalidArgument(f"Argument {name} not defined by handler")
            annotation = signature.parameters[name].annotation
            if annotation == inspect.Parameter.empty:
                # No annotation defined. Assume string
                continue

            args[name] = self.interpret_argument(annotation, value)

        try:
            return await command(**args)
        except RPCInvalidArgument as e:
            raise InvalidArgument(str(e))

    def interpret_argument(self, annotation, value):
        if isinstance(annotation, UnionType):
            errors = []
            for subannotation in typing.get_args(annotation):
                try:
                    return self.interpret_argument(subannotation, value)
                except InvalidArgument as e:
                    errors.append(str(e))
                    continue
            raise InvalidArgument(", ".join(errors))
        elif annotation == bool:
            return self.interpret_bool(value)
        else:
            try:
                return annotation(value)
            except ValueError as e:
                raise InvalidArgument(str(e))

    def interpret_bool(self, value: str) -> bool:
        value = value.lower()
        if value in ("1", "t", "true", "on", "yes"):
            return True
        elif value in ("0", "f", "false", "off", "no"):
            return False
        raise InvalidArgument(f'"{value}" could not be interpreted as boolean')

    def read_input(self):
        self.key_queue.put_nowait(sys.stdin.read(1))

    async def prompt(self):
        """
        Prompt and handle command if valid. Returns after each line
        """
        prompt = Prompt(stdout=self.stdout, history=self.history)

        with KeyReader(self.stdin) as keyreader:
            while True:
                key = await keyreader.get()
                if key == Key.ENTER:
                    if await prompt.enter():
                        # Break out of loop to handle command
                        self.stdout.write("\r\n")
                        break
                elif key == Key.DELETE_LEFT:
                    prompt.delete_left()
                elif key == Key.HOME:
                    prompt.cursor_home()
                elif key == Key.END:
                    prompt.cursor_end()
                elif key == Key.LEFT:
                    prompt.cursor_left()
                elif key == Key.RIGHT:
                    prompt.cursor_right()
                elif key == Key.UP:
                    prompt.up()
                elif key == Key.DOWN:
                    prompt.down()
                elif key == Key.DELETE_RIGHT:
                    prompt.delete_right()
                elif key == Key.TAB:
                    try:
                        async with asyncio.timeout(self.operation_timeout):
                            await prompt.complete(self.router.get_command_completions)
                    except TimeoutError:
                        prompt.display_message("\nTimed out getting completions")
                        return
                elif key == Key.SHIFT_TAB:
                    prompt.complete_previous()
                elif key == Key.EOF:
                    self.stdout.write("\r\n")
                    raise EOFError()
                elif key == Key.INTERRUPT:
                    self.stdout.write("\r\n")
                    raise KeyboardInterrupt()
                elif isinstance(key, Key):
                    # Unhandled keypress
                    pass
                else:
                    prompt.insert(key)

        if prompt.input:
            try:
                async with asyncio.timeout(self.operation_timeout):
                    output = await self.handle_command(prompt.input)
            except CommandNotFound as e:
                prompt.display_message(f"Command not found: {e}")
                return
            except InvalidArgument as e:
                prompt.display_message(f"Invalid argument: {e}")
                return
            except RPCUnspecifiedError as e:
                prompt.display_message("An unspecified error occured. See agent log.")
                return
            except TimeoutError:
                prompt.display_message("Timed out handling command")
                return

            if output is not None:
                prompt.display_message(output)

    async def main(self):
        if not self.stdin.isatty():
            for line in self.stdin.readlines():
                await self.handle_command(line)
            raise ServiceExit()

        loop = asyncio.get_running_loop()
        loop.add_reader(self.stdin.fileno(), self.read_input)

        term_attrs = termios.tcgetattr(self.stdin)
        tty.setraw(self.stdin)

        try:
            while True:
                try:
                    await self.prompt()
                except EOFError:
                    raise ServiceExit()
        finally:
            loop.remove_reader(self.stdin.fileno())
            termios.tcsetattr(self.stdin, termios.TCSAFLUSH, term_attrs)
            self.history.save()
