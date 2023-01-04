"""
routesia/cli/cli.py - Command line interface
"""
import asyncio
import os
from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
import shlex
import sys

from routesia.exceptions import CommandError
from routesia.rpc.client import AsyncRPCClient


CONFIG_PATH = os.path.expanduser("~/.config/routesia/")


class CLICommandTreeNode:
    """
    Represents a node in the command tree
    """

    def __init__(self, client, name):
        self.client = client
        self.name = name
        self.argument = "=" in self.name if self.name else False
        self.children = {}
        self.handler = None

    def dump(self, index=0):
        s = "    " * index
        if self.name:
            s += self.name + " "
        if self.handler:
            s += str(self.handler)
        if self.children:
            s += "->"
        print(s)
        for child in self.children.values():
            child.dump(index + 1)

    def insert_command(self, command, components):
        if not components:
            # Command is complete. handler goes here
            self.handler = command(self.client)
        else:
            component = components.pop(0)
            if component not in self.children:
                self.children[component] = CLICommandTreeNode(self.client, component)
            self.children[component].insert_command(command, components)

    def register_command(self, command):
        components = command.command.split()
        self.insert_command(command, components)

    def register_command_set(self, command_set):
        for command in command_set.commands:
            self.register_command(command)

    async def get_completions(self, args, suggestion):
        """
        Get completions based on args and suggestion. ``args`` is the list of
        previous arguments that have not been processed, and ``suggestion`` is
        the text of the current argument typed in so far.
        """
        if self.handler:
            return await self.handler.get_completions(args, suggestion)

        if args:
            arg = args.pop(0)
            if arg in self.children:
                return await self.children[arg].get_completions(args, suggestion)

        # Return all matching children
        return [key for key in self.children.keys() if key.startswith(suggestion)]

    async def handle(self, command):
        if self.handler:
            return await self.handler.handle(command)

        if command:
            arg = command.pop(0)
            if arg in self.children:
                return await self.children[arg].handle(command)

        print("Command incomplete or not found.")


class RoutesiaCompleter(Completer):
    def __init__(self, client, command_tree, *args, **kwargs):
        self.client = client
        self.command_tree = command_tree
        super().__init__(*args, **kwargs)

    def get_completions(self, document, complete_event):
        """
        Fake implementation since we only use the async variant.
        """
        return []

    async def get_completions_async(self, document, complete_event):
        text = document.text_before_cursor
        args = text.split()
        if not text or text[-1] == " ":
            suggestion = ""
        else:
            suggestion = args.pop(-1)

        for candidate in await self.command_tree.get_completions(args, suggestion):
            if isinstance(candidate, Completion):
                if str(candidate.text).startswith(suggestion):
                    yield Completion(
                        candidate.text,
                        display=candidate.display,
                        start_position=-1 * len(document.get_word_before_cursor(WORD=True)),
                    )
            elif candidate.startswith(suggestion):
                yield Completion(
                    candidate,
                    start_position=-1 * len(document.get_word_before_cursor(WORD=True)),
                )


class CLI:
    def __init__(self, host="localhost", port=1883, config_path=CONFIG_PATH):
        self.host = host
        self.port = port
        self.loop = asyncio.get_event_loop()
        self.client = AsyncRPCClient(self.loop, self.host, self.port)
        self.command_tree = CLICommandTreeNode(self.client, None)

    def register_command(self, command):
        self.command_tree.register_command(command)

    def register_command_set(self, command_set):
        self.command_tree.register_command_set(command_set)

    async def main(self):
        self.loop.create_task(self.client.run())
        await self.client.wait_connect()

        if not os.path.isdir(os.path.dirname(CONFIG_PATH)):
            os.makedirs(os.path.dirname(CONFIG_PATH), 0o700)

        session = PromptSession(
            HTML("<b>>>></b> "),
            completer=RoutesiaCompleter(self.client, self.command_tree),
            history=FileHistory("%s/rcl_history" % CONFIG_PATH),
        )

        while True:
            # Avoid garbling output when events occur
            with patch_stdout():
                try:
                    text = await session.prompt_async()
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                else:
                    text = text.strip()
                    if text:
                        try:
                            await self.command_tree.handle(shlex.split(text))
                        except CommandError as e:
                            print(e, file=sys.stderr)

    async def get_command_result(self, cmd):
        self.loop.create_task(self.client.run())
        await self.client.wait_connect()
        try:
            await self.command_tree.handle(shlex.split(cmd))
        except CommandError as e:
            print(e, file=sys.stderr)
            return 1

    def run(self):
        self.loop.run_until_complete(self.main())

    def run_command(self, cmd):
        return self.loop.run_until_complete(self.get_command_result(cmd))
