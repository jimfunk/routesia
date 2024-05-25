"""
hosteria/cli/__init__.py - CLI appplication
"""

import asyncio
from asyncio import Queue
from collections import OrderedDict
import logging
import sys
import termios
import tty

from routesia.cli.arguments import interpret_arguments
from routesia.cli.exceptions import (
    CommandNotFound,
    InvalidCommandDefinition,
    InvalidArgument,
    DuplicateArgument,
)
from routesia.cli.history import History
from routesia.cli.keyreader import KeyReader, Key
from routesia.cli.prompt import Prompt
from routesia.mqtt import MQTT
from routesia.rpc import RPCInvalidArgument, RPCUnspecifiedError
from routesia.rpcclient import RPCClient
from routesia.service import Provider


logger = logging.getLogger("cli")


class Fragment:
    """
    Represents a fragment of a command definition
    """

    def __init__(self, definition: str, namespace: str = None):
        self.definition: str = definition
        self.namespace = namespace

        self.name: str
        self.argument: bool = False
        self.keyword: bool = False
        self.repeated: bool = False
        self.completer: str = None

        if definition[0] in (":", "@", "*"):
            # Is an argument
            #  : - positional
            #  @ - keyword
            #  * - repeated keyword
            self.name = definition[1:]
            self.argument = True
            self.keyword = definition[0] == "@"
            self.repeated = definition[0] == "*"
        else:
            self.name = definition

        if "!" in self.name:
            # Completer option:
            #  ! - don't complete
            #  !<name> - use alternative completer name
            self.name, completer_def = self.name.split("!", 1)
            if completer_def:
                completer = completer_def
            else:
                completer = None
        else:
            completer = self.name

        if self.argument:
            self.completer = completer

    def __hash__(self) -> int:
        return hash(self.name)


class CommandNode:
    def __init__(self, fragment: Fragment = None):
        self.fragment = fragment

        self.children: dict[str:CommandNode] = {}
        self.handler: callable = None
        self.keyword_arguments: dict[str:Fragment] = {}

    def set_handler(self, handler: callable, keyword_arguments: list[Fragment] = None):
        self.handler = handler
        if keyword_arguments is not None:
            for keyword_argument in keyword_arguments:
                self.keyword_arguments[keyword_argument.name] = keyword_argument

    def match(
        self, fragments: list[str], completion: bool = False
    ) -> tuple["CommandNode", dict[str, str]]:
        """
        Return the child matching the given fragments.

        Returns a tuple of the matched command node and a dict of the parsed
        variable values.
        """
        if not fragments:
            return self, {}

        if fragments[0] in self.children:
            return self.children[fragments[0]].match(
                fragments[1:], completion=completion
            )
        else:
            for child in self.children.values():
                if child.fragment.argument:
                    args = OrderedDict()
                    args[child.fragment.name] = fragments[0]
                    node, child_args = child.match(fragments[1:], completion=completion)
                    if node:
                        args.update(child_args)
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
                        fragment = self.keyword_arguments[name]
                        if fragment.repeated:
                            if name in args:
                                args[name].append(value)
                            else:
                                args[name] = [value]
                        else:
                            if name in args:
                                raise DuplicateArgument(name)
                            args[name] = value
                    else:
                        raise InvalidArgument(name)

                return self, args

        raise CommandNotFound(fragments[0])


class CommandRouter:
    def __init__(self):
        self.root_node = CommandNode()
        # Indexed by namespace, then name. Namespace of None is global and
        # will be looked up if a namespaced completer is not found
        self.argument_completers: dict[str : dict[str:callable]] = {
            None: {
                "bool": self.complete_bool,
            }
        }

    def add(self, pattern: str, handler: callable, namespace: str = None):
        node = self.root_node
        keyword_arguments = []

        fragment_definitions = pattern.split()
        for i, fragment_definition in enumerate(fragment_definitions):
            fragment = Fragment(fragment_definition, namespace=namespace)

            # TODO: when there are positionals, the node is on the last
            # positional. It would be better to have it on the previous
            # non-argument fragment since we can better report missing
            # arguments instead of not finding the command at all.
            # Perhaps we can get the Fragment objects in a first pass and get
            # the position of the last non-argument node. However, that makes
            # having different handlers for different numbers of arguments
            # more difficult. Perhaps we keep it as is and report the
            # potential commands in the error?
            if fragment.keyword or fragment.repeated:
                # Start of keyword arguments. These are not placed in the node
                # tree since there is no ordering
                for fragment_definition in fragment_definitions[i:]:
                    fragment = Fragment(fragment_definition, namespace=namespace)
                    if fragment.keyword or fragment.repeated:
                        keyword_arguments.append(fragment)
                    else:
                        raise InvalidCommandDefinition(
                            f"Positional command fragment '{fragment_definition}' may not be defined after keyword arguments"
                        )
                break

            if fragment.name in node.children:
                node = node.children[fragment.name]
            else:
                new_node = CommandNode(fragment)
                node.children[fragment.name] = new_node
                node = new_node

        node.set_handler(handler, keyword_arguments)

    def add_argument_completer(
        self, name: str, completer: callable, namespace: str = None
    ):
        """
        Add an argument completer
        """
        if namespace not in self.argument_completers:
            self.argument_completers[namespace] = {}
        self.argument_completers[namespace][name] = completer

    def get_argument_completer(self, name: str, namespace: str = None) -> callable:
        """
        Get an argument completer for the given namespace if present. If
        namespace is not given, the global namespace is searched.

        If namespace is given and a completer was not found, the global
        namespace will be searched.
        """
        if namespace is None:
            return self.argument_completers[None].get(name, None)
        completer = None
        if namespace in self.argument_completers:
            completer = self.argument_completers[namespace].get(name, None)
        if not completer:
            completer = self.argument_completers[None].get(name, None)
        return completer

    def get_command_handler(self, command: str | list[str]) -> tuple[callable, dict]:
        """
        Get command handler and arguments from input command
        """
        if isinstance(command, str):
            fragments = command.split()
        else:
            fragments = command

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
        for child in node.children.values():
            if child.fragment.argument:
                if child.fragment.completer:
                    completer = self.get_argument_completer(
                        child.fragment.completer, child.fragment.namespace
                    )
                    if completer:
                        try:
                            for child_completion in await completer(
                                **interpret_arguments(completer, args)
                            ):
                                completions.append(child_completion)
                        except InvalidArgument:
                            pass
            else:
                completions.append(child.fragment.name)

        keyword_value = False
        if args:
            last_keyword_arg, last_keyword_value = list(args.items())[-1]
            if last_keyword_value is None and last_keyword_arg in node.keyword_arguments:
                keyword_value = True
                fragment = node.keyword_arguments[last_keyword_arg]
                if fragment.completer:
                    keyword_completer = self.get_argument_completer(
                        fragment.completer, fragment.namespace
                    )
                    if keyword_completer:
                        try:
                            for arg_completion in await keyword_completer(
                                **interpret_arguments(keyword_completer, args)
                            ):
                                completions.append(arg_completion)
                        except InvalidArgument:
                            pass

        if not keyword_value:
            for keyword_argument in node.keyword_arguments:
                if keyword_argument not in args:
                    completions.append(keyword_argument)

        return completions

    async def complete_bool(self, **args):
        return ["true", "false"]


class UndefinedNamespace(str):
    """
    Represents an undefined namespace
    """

    pass


class CLINamespace:
    """
    This represents a cli module. Its main purpose is to act as a namespace
    for completers and node lookups to avoid accidental overrides on completer
    definitions.
    """

    def __init__(self, cli: "CLI", namespace: str):
        self.cli = cli
        self.namespace = namespace

    def add_argument_completer(
        self, name: str, completer: callable, namespace: str = UndefinedNamespace
    ):
        self.cli.add_argument_completer.__doc__
        if namespace is UndefinedNamespace:
            namespace = self.namespace
        self.cli.add_argument_completer(name, completer, namespace=namespace)

    def add_command(
        self, pattern: str, handler: callable, namespace: str = UndefinedNamespace
    ):
        self.cli.add_command.__doc__
        if namespace is UndefinedNamespace:
            namespace = self.namespace
        self.cli.add_command(pattern, handler, namespace=namespace)


class CLI(Provider):
    def __init__(
        self,
        rpcclient: RPCClient,
        mqtt: MQTT,
        stdin=sys.stdin,
        stdout=sys.stdout,
        operation_timeout=5,
    ):
        super().__init__()
        self.rpcclient = rpcclient
        self.mqtt = mqtt
        self.stdin = stdin
        self.stdout = stdout
        self.operation_timeout = operation_timeout

        self.application = None
        self.router = CommandRouter()
        self.key_queue = Queue(maxsize=65535)
        self.history = History()
        self.connected = False

    def get_namespace_cli(self, namespace: str) -> CLINamespace:
        return CLINamespace(self, namespace)

    def add_command(self, pattern: str, handler: callable, namespace: str = None):
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
        completion for it in one instance, append the ``!`` character to it.
        You can also make an argument complete using a different completer
        name by adding ``!`` followed by the desired completer name.

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
        self.router.add(pattern, handler, namespace)

    def add_argument_completer(
        self, name: str, completer: callable, namespace: str = None
    ):
        """
        Add an argument completer

        The completer must be a callable that returns a list of strings used
        for completion matching.

        If a command has multiple arguments, arguments defined to the left
        will be passed to the completer.
        """
        self.router.add_argument_completer(name, completer, namespace=namespace)

    async def handle_command(self, cmd: str | list[str]):
        command, args = self.router.get_command_handler(cmd)
        args = interpret_arguments(command, args, required=True)

        try:
            return await command(**args)
        except RPCInvalidArgument as e:
            raise InvalidArgument(str(e))

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

    async def run_command(self, command: str | list[str]) -> int:
        """
        Run a single command.

        The command may be given as a single string or a list of strings representing
        the command fragments.
        """
        if not self.connected:
            try:
                async with asyncio.timeout(self.operation_timeout):
                    await self.mqtt.wait_connect()
            except asyncio.Timeout:
                print("Timed out connecting to broker", file=sys.stderr)
                return 1
            self.connected = True

        try:
            async with asyncio.timeout(self.operation_timeout):
                output = await self.handle_command(command)
        except CommandNotFound as e:
            print(f"Command not found: {e}", file=sys.stderr)
            return 1
        except InvalidArgument as e:
            print(f"Invalid argument: {e}", file=sys.stderr)
            return 1
        except RPCUnspecifiedError as e:
            print("An unspecified error occured. See agent log.", file=sys.stderr)
            return 1
        except TimeoutError:
            print("Timed out handling command", file=sys.stderr)
            return 1

        if output is not None:
            print(output)

        return 0

    async def run_repl(self) -> int:
        """
        Run the interactive REPL.
        """
        loop = asyncio.get_running_loop()
        loop.add_reader(self.stdin.fileno(), self.read_input)

        term_attrs = termios.tcgetattr(self.stdin)
        tty.setraw(self.stdin)

        try:
            while True:
                try:
                    await self.prompt()
                except EOFError:
                    break
        finally:
            loop.remove_reader(self.stdin.fileno())
            termios.tcsetattr(self.stdin, termios.TCSAFLUSH, term_attrs)
            self.history.save()

        return 0
