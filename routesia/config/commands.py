"""
routesia/config/commands.py - Routesia config commands
"""
import difflib

from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String
from routesia.config import config_pb2
from routesia.exceptions import CommandError


class Show(CLICommand):
    topic = None
    parameters = (("section", String()),)

    async def call(self, section=None, **kwargs):
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


class ShowRunning(Show):
    command = "config running show"
    topic = "/config/running/get"


class ShowStaged(Show):
    command = "config staged show"
    topic = "/config/staged/get"


class Diff(Show):
    command = "config diff"

    async def call(self, section=None, **kwargs):
        data = await self.client.request("/config/running/get", None)
        running_config = config_pb2.Config.FromString(data)
        data = await self.client.request("/config/staged/get", None)
        staged_config = config_pb2.Config.FromString(data)

        if section:
            if not hasattr(running_config, section):
                raise CommandError('Section "%s" not in config' % section)
            running_config = getattr(running_config, section)
            staged_config = getattr(staged_config, section)

        return "\n".join(
            list(
                difflib.unified_diff(
                    str(running_config).splitlines(),
                    str(staged_config).splitlines(),
                    lineterm="",
                )
            )[2:]
        )


class Commit(CLICommand):
    command = "config commit"

    async def call(self, **kwargs):
        data = await self.client.request("/config/staged/commit", None)
        return config_pb2.CommitResult.FromString(data)


class ConfigCommandSet(CLICommandSet):
    commands = (
        ShowRunning,
        ShowStaged,
        Diff,
        Commit,
    )
