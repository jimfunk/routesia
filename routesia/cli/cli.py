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

from routesia.rpc.client import AsyncRPCClient


CONFIG_PATH = os.path.expanduser('~/.config/routesia/')


class CLICommandTreeNode:
    """
    Represents a node in the command tree
    """

    def __init__(self, name):
        self.name = name
        self.argument = '=' in self.name if self.name else False
        self.children = {}
        self.handler = None

    def dump(self, index=0):
        s = '    ' * index
        if self.name:
            s += self.name + ' '
        if self.handler:
            s += str(self.handler)
        if self.children:
            s += '->'
        print(s)
        for child in self.children.values():
            child.dump(index + 1)

    async def get_completions(self, client, args, suggestion, index=0):
        """
        Get completions based on args and suggestion. ``args`` is the list of
        previous arguments and ``suggestion`` is the text of the current
        argument typed in so far. The index indicates which argument is under
        consideration as this traverses the tree.
        """
        if self.handler:
            # We are at the bottom. pass to the handler
            return await self.handler.get_completions(client, args, suggestion, index)

        if len(args) > index:
            # Pass to lower

            if args[index] in self.children:
                return await self.children[args[index]].get_completions(client, args, suggestion, index+1)
            return []

        # Return all children
        return self.children.keys()

    async def handle(self, client, command):
        if self.handler:
            return await self.handler(client)

        if command:
            arg = command.pop(0)
            if arg in self.children:
                return await self.children[arg].handle(client, command)

        print("Command incomplete or not found.")


class RoutesiaCompleter(Completer):
    def __init__(self, cli, client, *args, **kwargs):
        self.cli = cli
        self.client = client
        super().__init__(*args, **kwargs)

    def get_completions(self, document, complete_event):
        """
        Fake implementation since we only use the async variant.
        """
        return []

    async def get_completions_async(self, document, complete_event):
        text = document.text_before_cursor
        args = text.split()
        if not text or text[-1] == ' ':
            suggestion = ''
        else:
            suggestion = args.pop(-1)

        for candidate in await self.cli.command_tree.get_completions(self.client, args, suggestion):
            if candidate.startswith(suggestion):
                yield Completion(candidate, start_position=-1 * len(document.get_word_before_cursor()))


class CLI:
    def __init__(self, host='localhost', port=1883, config_path=CONFIG_PATH):
        self.host = host
        self.port = port
        self.command_tree = CLICommandTreeNode(None)

    def insert_command(self, node, command, index=0):
        if index == len(command.command):
            # Command is complete. handler goes here
            node.handler = command()
        else:
            component = command.command[index]
            if component not in node.children:
                node.children[component] = CLICommandTreeNode(component)
            self.insert_command(node.children[component], command, index+1)

    def register_command_set(self, command_set):
        for command in command_set.commands:
            self.insert_command(self.command_tree, command)

    async def main(self, loop):
        self.command_tree.dump()

        client = AsyncRPCClient(loop, self.host, self.port)
        loop.create_task(client.run())

        session = PromptSession(
            HTML('<b>>>></b> '),
            completer=RoutesiaCompleter(self, client),
            history=FileHistory('%s/rcl_history' % CONFIG_PATH),
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
                        await self.command_tree.handle(client, shlex.split(text))

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main(loop))
