"""
routesia/config/commands.py - Routesia config commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.config import config_pb2


class ConfigGetRunning(CLICommand):
    command = ('get', 'config', 'running')

    async def __call__(self, client):
        data = await client.request('/config/running/get', None)
        config = config_pb2.Config.FromString(data)
        print(config)


class ConfigGetStaged(CLICommand):
    command = ('get', 'config', 'staged')

    async def __call__(self, client):
        data = await client.request('/config/staged/get', None)
        config = config_pb2.Config.FromString(data)
        print(config)


class ConfigCommit(CLICommand):
    command = ('commit',)

    async def __call__(self, client):
        data = await client.request('/config/staged/commit', None)
        result = config_pb2.CommitResult.FromString(data)
        print(result.message)


class ConfigCommandSet(CLICommandSet):
    commands = (
        ConfigGetRunning,
        ConfigGetStaged,
        ConfigCommit,
    )
