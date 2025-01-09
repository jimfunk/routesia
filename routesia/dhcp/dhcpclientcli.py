"""
routesia/dhcp/client/cli.py - Routesia DHCP client commands
"""

from routesia.cli import CLI, InvalidArgument
from routesia.cli.completion import Completion
from routesia.cli.types import UInt32
from routesia.rpcclient import RPCClient
from routesia.schema.v2 import dhcp_client_pb2
from routesia.service import Provider


class DHCPClientCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("dhcp-client")
        self.rpc = rpc

        self.cli.add_argument_completer("system-interface", self.complete_system_interface)
        self.cli.add_argument_completer("interface", self.complete_interface)
        self.cli.add_argument_completer("table", self.complete_table)

        self.cli.add_command("dhcp client config get", self.get_config)
        self.cli.add_command("dhcp client v4 add :interface!system-interface @table", self.add_config)
        self.cli.add_command(
            "dhcp client v4 config update :interface @table", self.update_config
        )
        self.cli.add_command(
            "dhcp client v4 config delete :interface", self.delete_config
        )
        self.cli.add_command("dhcp client v4 show", self.show)
        self.cli.add_command("dhcp client v4 show :interface", self.show)
        self.cli.add_command("dhcp client v4 restart :interface", self.restart)

    async def complete_system_interface(self):
        interfaces = []
        interface_list = await self.rpc.request("interface/list")
        for interface in interface_list.interface:
            interfaces.append(interface.name)
        return interfaces

    async def complete_interface(self):
        completions = []
        statuslist = await self.rpc.request("dhcp/client/v4/list")
        for client in statuslist.client:
            completions.append(client.interface)
        return completions

    async def complete_table(self):
        completions = []
        config = await self.rpc.request("route/table/list", None)
        for table in config.v4:
            completions.append(Completion(str(table.id), f"{table.id} {table.name}"))
        return completions

    async def get_config(self):
        return await self.rpc.request("dhcp/client/config/get")

    async def show(self, interface: str = None):
        statuslist = await self.rpc.request("dhcp/client/v4/list")
        if interface:
            for client in statuslist.client:
                if client.interface == interface:
                    return client
            raise InvalidArgument("No such client for interface: %s" % interface)
        return statuslist

    async def restart(self, interface: str):
        config = dhcp_client_pb2.DHCPv4ClientConfig()
        config.interface = interface
        return await self.rpc.request("dhcp/client/v4/restart", config)

    async def add_config(self, interface: str, table: UInt32 = None):
        client = dhcp_client_pb2.DHCPv4ClientConfig()
        client.interface = interface
        if table is not None:
            client.table = table
        return await self.rpc.request("dhcp/client/config/v4/add", client)

    async def update_config(self, interface: str, table: UInt32 = None):
        config = await self.rpc.request("dhcp/client/config/get", None)
        client = None
        for client_object in config.v4:
            if client_object.interface == interface:
                client = client_object
        if not client:
            raise InvalidArgument("No such client for interface: %s" % interface)
        if table is not None:
            client.table = table
        await self.rpc.request("dhcp/client/config/v4/update", client)

    async def delete_config(self, interface: str):
        client = dhcp_client_pb2.DHCPv4ClientConfig()
        client.interface = interface
        await self.rpc.request("dhcp/client/config/v4/delete", client)
