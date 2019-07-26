import difflib
from google.protobuf import text_format
import os

from routesia import config_pb2
from routesia.command import CommandProvider, CommandHandler
from routesia.injector import Provider

SCHEMA = "1.0"


class ConfigProvider(Provider):
    def __init__(self, location='/etc/routesia/config'):
        self.location = location
        self.data = config_pb2.Config()
        self.staged_data = config_pb2.Config()
        self.init_config_hooks = []

    @property
    def config_file(self):
        return '%s/%s.conf' % (self.location, self.version)

    def get_latest_config_version(self):
        latest = None
        for filename in os.listdir(self.location):
            if '.' in filename:
                base, ext = filename.split('.', 1)
                if ext == 'conf' and base.isdigit():
                    version = int(base)
                    if latest is None or version > latest:
                        latest = version
        return latest

    def register_init_config_hook(self, hook):
        self.init_config_hooks.append(hook)

    def init_config(self):
        self.version = 0
        self.data.system.schema = SCHEMA
        self.data.system.version = self.version
        for hook in self.init_config_hooks:
            hook(self.data)
        self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            f.write(str(self.data))

    def load_config(self):
        with open(self.config_file) as f:
            text_format.Merge(f.read(), self.data)

    def load(self):
        if not os.path.isdir(self.location):
            os.makedirs(self.location, 0o700)

        self.version = self.get_latest_config_version()

        if self.version is not None:
            self.load_config()
        else:
            self.init_config()

    def get_entity_completion(self, data, args):
        if not args:
            return data
        if hasattr(data, args[0]):
            return self.get_get_entity_config(getattr(data, args[0]), args[1:])
        return None

    def get_entity_config(self, data, args):
        if not args:
            return data
        print(args[0])
        if args[0] in data.DESCRIPTOR.fields_by_name:
            field = data.DESCRIPTOR.fields_by_name[args[0]]
            if field.label == field.LABEL_REPEATED:
                if len(args) == 1:
                    # Return all items
                    return getattr(data, args[0])
                else:
                    # Return item where the primary field matches arg[1]
                    for item in getattr(data, args[0]):
                        primary = getattr(item, item.DESCRIPTOR.fields[0].name)
                        if primary == args[1]:
                            return self.get_get_entity_config(item, args[2:])
            else:
                return self.get_get_entity_config(getattr(data, args[0]), args[1:])
        return None

    def startup(self, command: CommandProvider):
        self.staged_data.CopyFrom(self.data)
        command.register_command(GetCommand(self))
        command.register_command(ShowRunningConfigCommand(self))
        command.register_command(ShowChangesCommand())


class ShowRunningConfigCommand(CommandHandler):
    name = "show-running-config"
    short_help = "Show running configuration."
    long_help = "Show full running configuration."

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    def get_candidates(self, data, args):
        if len(args) == 1:
            candidates = []
            for field in data.DESCRIPTOR.fields:
                if field.name.startswith(args[0]):
                    candidates.append(field.name)
            return candidates
        if hasattr(data, args[0]):
            return self.get_candidates(getattr(data, args[0]), args[1:])
        return []

    def handle_completion(self, request):
        try:
            return self.get_candidates(self.config.data, request.argument)
        except Exception as e:
            print(e)
            raise e

    def get_section(self, data, args):
        if hasattr(data, args[0]):
            if len(args) == 1:
                return getattr(data, args[0])
            return self.get_section(data, args[1:])

    def handle(self, cmd):
        data = self.config.data

        if cmd.argument:
            data = self.get_section(data, cmd.argument)

        return str(data)


class GetCommand(CommandHandler):
    name = "get"
    short_help = "Get configuration."
    long_help = "Get configuration for an entity."

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    # def handle_completion(self, request):
    #     return self.config.get_entity_completion(self.config.staged_data, request.argument)

    def handle(self, cmd):
        data = self.config.staged_data

        if cmd.argument:
            data = self.config.get_entity_config(data, cmd.argument)

        return str(data)


class SetCommand(CommandHandler):
    name = "set"
    short_help = "Set configuration item(s)."
    long_help = "Set configuration item or items for an entity."

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    def get_candidates(self, data, args):
        if len(args) == 1:
            candidates = []
            for field in data.DESCRIPTOR.fields:
                if field.name.startswith(args[0]):
                    candidates.append(field.name)
            return candidates
        if hasattr(data, args[0]):
            return self.get_candidates(getattr(data, args[0]), args[1:])
        return []

    def handle_completion(self, request):
        return self.get_candidates(self.config.data, request.argument)

    def get_section(self, data, args):
        if hasattr(data, args[0]):
            if len(args) == 1:
                return getattr(data, args[0])
            return self.get_section(data, args[1:])

    def handle(self, cmd):
        data = self.config.data

        if cmd.argument:
            data = self.get_section(data, cmd.argument)

        return str(data)


class ShowChangesCommand(CommandHandler):
    name = "show-changes"
    short_help = "Show staged configuration changes."
    long_help = "Show staged changes to the configuration."

    def handle(self, cmd, config: ConfigProvider):
        return '\n'.join(difflib.unified_diff(config.data.split('\n'), config.staged_data.split('\n')))
