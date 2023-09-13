"""
hosteria/cli/__init__.py - CLI appplication
"""

import asyncio
from asyncio import Queue
import sys
import termios
import tty

from routesia.cli.keyreader import KeyReader, Key
from routesia.cli.prompt import Prompt
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

    def set_handler(self, handler, keyword_arguments=None, keyword_list_arguments=None):
        self.handler = handler
        if keyword_arguments is not None:
            self.keyword_arguments = set(keyword_arguments)
        if keyword_list_arguments is not None:
            self.keyword_list_arguments = set(keyword_list_arguments)

    def match(self, fragments: list[str]) -> tuple["CommandNode", dict[str, str]]:
        """
        Return the child matching the given fragments.

        Returns a tuple of the matched command node and a dict of the parsed
        variable values.
        """
        if not fragments:
            return self, {}

        if fragments[0] in self.children:
            return self.children[fragments[0]].match(fragments[1:])
        else:
            for name, child in self.children.items():
                if name.startswith(":"):
                    node, args = child.match(fragments[1:])
                    if node:
                        args[name[1:]] = fragments[0]
                        return node, args
            if self.handler:
                # Check the remaining fragments for keyword arguments
                keyword_fragments = fragments[:]
                args = {}
                while keyword_fragments:
                    if len(keyword_fragments) < 2:
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
            node, args = self.root_node.match(fragments)
        except CommandNotFound:
            return []

        completions = []
        for child in node.children:
            if child.startswith(":"):
                completer = self.argument_completers.get(child[1:], None)
                if completer:
                    for child_completion in await completer(**args):
                        completions.append(child_completion)
            else:
                completions.append(child)

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

    def add_command(self, pattern: str, handler: callable):
        """
        Add a command

        The command must be a coroutine.

        The pattern represents the command as typed. For example:

            show foo

        If a component of the pattern starts with ``:`` it will represent an
        argument that will be passed to the handler. The argument should be
        added using the ``add_argument_completer()`` method if completion is
        desired.

        For example:

            show foo :bar

        Commands may also define keyword arguments. Each argument must start
        with a character indicating how it is to be interpreted:

            ``@``: May only be specified once
            ``*``: May be specified multiple times

        Keyword arguments must always be defined after positional arguments.
        They are expected to be entered in the command as 2 arguments,
        starting with the variable name, eg: ``argument-name value``.

        All variables and arguments will be passed to the handler as keyword
        arguments, even when defined as positional in the pattern.

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
        command, args = self.router.get_command_handler(cmd)
        return await command(**args)

    def read_input(self):
        self.key_queue.put_nowait(sys.stdin.read(1))

    async def prompt(self):
        """
        Prompt and handle command if valid. Returns after each line
        """
        prompt = Prompt(stdout=self.stdout)

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
            except TimeoutError as e:
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
