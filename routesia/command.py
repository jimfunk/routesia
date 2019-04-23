"""
routesia/command.py - Command line support
"""

from collections import OrderedDict

from routesia.exceptions import CommandNotFound
from routesia.injector import Provider, Injector
from routesia.mqtt import MQTT


class CommandHandler:
    name = None
    required_arguments = []
    optional_arguments = []
    short_help = "Missing short_help"
    long_help = "Missing long_help"

    def handle(self, *args):
        raise NotImplementedError


class HelpCommand(CommandHandler):
    name = "help"
    short_help = "Show help."
    long_help = "If called without arguments, show all available commands. If called with a command name, show detailed help for that command."

    def handle(self, command: 'CommandProvider', name=None):
        if name:
            if name in command.commands:
                return command.commands[name].long_help
            else:
                return 'Command "%s" not found.' % name

        s = ''
        for name, handler in command.commands.items():
            s += '%s - %s\n' % (name, handler.short_help)
        return s


class CommandProvider(Provider):
    def __init__(self, mqtt: MQTT, injector: Injector):
        super().__init__()
        self.mqtt = mqtt
        self.injector = injector
        self.commands = OrderedDict()

    def register_command(self, handler: CommandHandler):
        self.commands[handler.name] = handler

    def run_command(self, name, kwargs):
        if name not in self.commands:
            raise CommandNotFound(name)
        self.injector.run(self.commands[name].handle, **kwargs)

    def handle_command(self, message):
        print(message)

    def startup(self):
        self.mqtt.subscribe('command/#', self.handle_command)
