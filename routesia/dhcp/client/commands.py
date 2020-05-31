"""
routesia/dhcp/client/commands.py - Routesia DHCP client commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String, UInt32
from routesia.dhcp.client import dhcpclient_pb2
from routesia.exceptions import CommandError
from routesia.interface.commands import ConfiguredInterfaceParameter
from routesia.route.commands import get_config_table_completions


async def get_v4_interface_completions(client, suggestion, **kwargs):
    completions = []
    statuslist = dhcpclient_pb2.DHCPv4ClientStatusList.FromString(
        await client.request("/dhcp/client/v4/list", None)
    )
    for client in statuslist.client:
        completions.append(client.interface)
    return completions


class DHCPClientV4Show(CLICommand):
    command = "dhcp client v4 show"
    parameters = (
        ("interface", String(max_length=15, completer=get_v4_interface_completions)),
    )

    async def call(self, interface=None):
        statuslist = dhcpclient_pb2.DHCPv4ClientStatusList.FromString(
            await self.client.request("/dhcp/client/v4/list", None)
        )
        if interface:
            for client in statuslist.client:
                if client.interface == interface:
                    return client
            raise CommandError("No such client for interface: %s" % interface)
        return statuslist


class DHCPClientV4Restart(CLICommand):
    command = "dhcp client v4 restart"
    parameters = (
        (
            "interface",
            String(
                required=True, max_length=15, completer=get_v4_interface_completions
            ),
        ),
    )

    async def call(self, interface):
        config = dhcpclient_pb2.DHCPv4ClientConfig()
        config.interface = interface
        await self.client.request("/dhcp/client/v4/restart", config)


async def get_v4_config_interface_completions(client, suggestion, **kwargs):
    completions = []
    config = dhcpclient_pb2.DHCPClientConfig.FromString(
        await client.request("/dhcp/client/config/get", None)
    )
    for client in config.v4:
        completions.append(client.interface)
    return completions


class DHCPClientConfigGet(CLICommand):
    command = "dhcp client config get"

    async def call(self):
        return dhcpclient_pb2.DHCPClientConfig.FromString(
            await self.client.request("/dhcp/client/config/get", None)
        )


class DHCPClientConfigV4Add(CLICommand):
    command = "dhcp client v4 config add"
    parameters = (
        ("interface", ConfiguredInterfaceParameter(required=True)),
        ("table", UInt32(completer=get_config_table_completions)),
    )

    async def call(self, interface, **kwargs):
        client = dhcpclient_pb2.DHCPv4ClientConfig()
        client.interface = interface
        self.update_message_from_args(client, **kwargs)
        await self.client.request("/dhcp/client/config/v4/add", client)


class DHCPClientConfigV4Update(CLICommand):
    command = "dhcp client v4 config update"
    parameters = (
        (
            "interface",
            String(
                required=True,
                max_length=15,
                completer=get_v4_config_interface_completions,
            ),
        ),
        ("table", UInt32(completer=get_config_table_completions)),
    )

    async def call(self, interface, **kwargs):
        config = dhcpclient_pb2.DHCPClientConfig.FromString(
            await self.client.request("/dhcp/client/config/get", None)
        )
        client = None
        for client_object in config.v4:
            if client_object.interface == interface:
                client = client_object
        if not client:
            raise CommandError("No such client for interface: %s" % interface)
        self.update_message_from_args(client, **kwargs)
        await self.client.request("/dhcp/client/config/v4/update", client)


class DHCPClientConfigV4Delete(CLICommand):
    command = "dhcp client v4 config delete"
    parameters = (
        (
            "interface",
            String(
                required=True,
                max_length=15,
                completer=get_v4_config_interface_completions,
            ),
        ),
    )

    async def call(self, interface, **kwargs):
        client = dhcpclient_pb2.DHCPv4ClientConfig()
        client.interface = interface
        await self.client.request("/dhcp/client/config/v4/delete", client)


class DHCPClientCommandSet(CLICommandSet):
    commands = (
        DHCPClientV4Show,
        DHCPClientV4Restart,
        DHCPClientConfigGet,
        DHCPClientConfigV4Add,
        DHCPClientConfigV4Update,
        DHCPClientConfigV4Delete,
    )
