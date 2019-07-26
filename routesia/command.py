"""
routesia/command.py - Command line support
"""

from collections import OrderedDict
import logging

from routesia.command_pb2 import CommandRequest, CommandResponse, CompletionRequest, CompletionResponse
from routesia.exceptions import CommandError
from routesia.injector import Provider, Injector
from routesia.mqtt import MQTT


logger = logging.getLogger(__name__)


class CommandHandler:
    name = None
    required_arguments = []
    optional_arguments = []
    short_help = "Missing short_help"
    long_help = "Missing long_help"

    def handle(self, *args):
        raise NotImplementedError

    def handle_completion(self, request):
        return []


class CommandProvider(Provider):
    def __init__(self, mqtt: MQTT, injector: Injector):
        super().__init__()
        self.mqtt = mqtt
        self.injector = injector
        self.commands = OrderedDict()
        self.register_command(HelpCommand())

    def register_command(self, handler: CommandHandler):
        self.commands[handler.name] = handler

    def run_command(self, cmd):
        response = CommandResponse()
        response.id = cmd.id

        if cmd.name not in self.commands:
            response.response_code = CommandResponse.COMMAND_NOT_FOUND
            return response
        try:
            content = self.injector.run(self.commands[cmd.name].handle, cmd=cmd)
        except CommandError as e:
            response.response_code = CommandResponse.COMMAND_ERROR
            response.content = str(e)
            return response
        except Exception as e:
            logger.exception(e)
            response.response_code = CommandResponse.UNSPECIFIED_ERROR
            return response

        response.response_code = CommandResponse.OK
        response.content = content

        return response

    def handle_command(self, message):
        cmd = CommandRequest()
        client_id = message.topic.rsplit('/')[-1]
        cmd.MergeFromString(message.payload)

        response = self.run_command(cmd)

        self.mqtt.publish('/command/response/%s' % client_id, payload=response.SerializeToString())

    def handle_completion(self, message):
        request = CompletionRequest()
        client_id = message.topic.rsplit('/')[-1]
        request.MergeFromString(message.payload)

        response = CompletionResponse()
        response.id = request.id

        candidates = []

        if request.name in self.commands.keys():
            if request.argument:
                try:
                    candidates = self.commands[request.name].handle_completion(request)
                except Exception as e:
                    logger.exception(e)
            else:
                candidates = [request.name]
        elif not request.argument:
            for name in self.commands.keys():
                if name.startswith(request.name):
                    candidates.append(name)

        for candidate in candidates:
            response.candidate.append(candidate)

        self.mqtt.publish('/command/completionresponse/%s' % client_id, payload=response.SerializeToString())

    def startup(self):
        self.mqtt.subscribe('/command/request/+', self.handle_command)
        self.mqtt.subscribe('/command/completionrequest/+', self.handle_completion)


class HelpCommand(CommandHandler):
    name = "help"
    short_help = "Show help."
    long_help = "If called without arguments, show all available commands. If called with a command name, show detailed help for that command."

    def handle(self, cmd, command: CommandProvider):
        if cmd.argument:
            if cmd.argument[0] in command.commands:
                return command.commands[cmd.argument[0]].long_help
            else:
                return 'Command "%s" not found.' % cmd.argument[0]

        s = ''
        for name, handler in command.commands.items():
            s += '%s - %s\n' % (name, handler.short_help)
        return s
