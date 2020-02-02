"""
routesia/config/commands.py - Routesia config commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.config import config_pb2
from routesia.exceptions import CommandError


class ShowConfig(CLICommand):
    topic = None

    async def call(self, section=None):
        data = await self.client.request(self.topic, None)
        config = config_pb2.Config.FromString(data)
        if section:
            if not hasattr(config, section):
                raise CommandError('Section "%s" not in config' % section)
            return getattr(config, section)
        return config

    async def get_section_completions(self, suggestion, *args, **kwargs):
        completions = []
        for field in config_pb2.Config.DESCRIPTOR.fields:
            if field.name.startswith(suggestion):
                completions.append(field.name)
        return completions


class ShowConfigRunning(ShowConfig):
    command = 'config running show'
    topic = '/config/running/get'


class ShowConfigStaged(CLICommand):
    command = 'config staged show'
    topic = '/config/staged/get'


class Commit(CLICommand):
    command = 'config staged commit'

    async def call(self):
        data = await self.client.request('/config/staged/commit', None)
        return config_pb2.CommitResult.FromString(data)


class ConfigCommandSet(CLICommandSet):
    commands = (
        ShowConfigRunning,
        ShowConfigStaged,
        Commit,
    )
