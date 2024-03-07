"""
routesia/config/commands.py - Routesia config commands
"""
import difflib

from routesia.cli import CLI, InvalidArgument
from routesia.rpcclient import RPCClient
from routesia.service import Provider


class ConfigCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli
        self.rpc = rpc

        self.cli.add_argument_completer("section", self.complete_sections)

        self.cli.add_command("config running show", self.show_running_config)
        self.cli.add_command("config running show :section", self.show_running_config)
        self.cli.add_command("config staged show", self.show_staged_config)
        self.cli.add_command("config staged show :section", self.show_staged_config)
        self.cli.add_command("config diff", self.diff)
        self.cli.add_command("config diff :section", self.diff)
        self.cli.add_command("config drop", self.drop)
        self.cli.add_command("config commit", self.commit)

    async def complete_sections(self, **args):
        return [
            "addresses",
            "dhcp",
            "dns",
            "interfaces",
            "ipam",
            "netfilter",
            "route",
            "system",
        ]

    async def show_running_config(self, section=None):
        config = await self.rpc.request("config/running/get")
        if section:
            if not hasattr(config, section):
                raise InvalidArgument('Section "%s" not in config' % section)
            return getattr(config, section)

        return config

    async def show_staged_config(self, section=None):
        config = await self.rpc.request("config/staged/get")
        if section:
            if not hasattr(config, section):
                raise InvalidArgument('Section "%s" not in config' % section)
            return getattr(config, section)

        return config

    async def diff(self, section=None):
        running_config = await self.rpc.request("config/running/get")
        staged_config = await self.rpc.request("config/staged/get")
        if section:
            if not hasattr(running_config, section):
                raise InvalidArgument('Section "%s" not in config' % section)
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

    async def drop(self):
        return await self.rpc.request("config/staged/drop")

    async def commit(self):
        return await self.rpc.request("config/staged/commit")
