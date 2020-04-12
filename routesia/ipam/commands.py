"""
routesia/ipam/commands.py - Routesia IPAM commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String, HardwareAddress, IPAddress
from routesia.exceptions import CommandError
from routesia.ipam import ipam_pb2


class IPAMConfigHostList(CLICommand):
    command = "ipam config host list"

    async def call(self, **kwargs):
        return ipam_pb2.IPAMConfig.FromString(
            await self.client.request("/ipam/config/host/list", None)
        )


class IPAMConfigHostAdd(CLICommand):
    command = "ipam config host add"
    parameters = (
        ("name", String(required=True)),
        ("hardware-address", HardwareAddress()),
    )

    async def call(self, name, **kwargs):
        host = ipam_pb2.Host()
        host.name = name
        self.update_message_from_args(host, **kwargs)
        await self.client.request("/ipam/config/host/add", host)


class IPAMConfigHostUpdate(CLICommand):
    command = "ipam config host update"
    parameters = (
        ("name", String(required=True)),
        ("hardware-address", HardwareAddress()),
    )

    async def call(self, name, **kwargs):
        host = ipam_pb2.Host()
        host.name = name
        self.update_message_from_args(host, **kwargs)
        await self.client.request("/ipam/config/host/update", host)


class IPAMConfigHostRemove(CLICommand):
    command = "ipam config host remove"
    parameters = (
        ("name", String(required=True)),
    )

    async def call(self, name, **kwargs):
        host = ipam_pb2.Host()
        host.name = name
        await self.client.request("/ipam/config/host/remove", host)


class HostCommand(CLICommand):
    async def get_host(self, name):
        config = ipam_pb2.IPAMConfig.FromString(
            await self.client.request("/ipam/config/host/list", None)
        )
        for host in config.host:
            if host.name == name:
                return host
        raise CommandError("Host %s not found" % name)


async def get_host_completions(client, suggestion, **kwargs):
    completions = []
    config = ipam_pb2.IPAMConfig.FromString(
        await client.request("/ipam/config/host/list", None)
    )
    for host in config.host:
        completions.append(host.name)
    return completions


async def get_host_alias_completions(client, suggestion, **kwargs):
    completions = []
    if "host" not in kwargs:
        return completions
    config = ipam_pb2.IPAMConfig.FromString(
        await client.request("/ipam/config/host/list", None)
    )
    for host in config.host:
        if host.name == kwargs["host"]:
            break
    else:
        return completions
    for alias in host.alias:
        completions.append(alias)
    return completions


async def get_host_address_completions(client, suggestion, **kwargs):
    completions = []
    if "host" not in kwargs:
        return completions
    config = ipam_pb2.IPAMConfig.FromString(
        await client.request("/ipam/config/host/list", None)
    )
    for host in config.host:
        if host.name == kwargs["host"]:
            break
    else:
        return completions
    for ip_address in host.ip_address:
        completions.append(ip_address)
    return completions


class IPAMConfigHostAliasAdd(HostCommand):
    command = "ipam config host alias add"
    parameters = (
        ("host", String(required=True, completer=get_host_completions)),
        ("alias", String(required=True)),
    )

    async def call(self, host, alias, **kwargs):
        host = await self.get_host(host)
        for alias_name in host.alias:
            if alias_name == alias:
                raise CommandError("Alias %s already exists for host %s" % (alias, host))
        host.alias.append(alias)
        await self.client.request("/ipam/config/host/update", host)


class IPAMConfigHostAliasRemove(HostCommand):
    command = "ipam config host alias remove"
    parameters = (
        ("host", String(required=True, completer=get_host_completions)),
        ("alias", String(required=True, completer=get_host_alias_completions)),
    )

    async def call(self, host, alias, **kwargs):
        host = await self.get_host(host)
        for i, alias_name in enumerate(host.alias_name):
            if alias_name == alias:
                del host.alias[i]
                break
        await self.client.request("/ipam/config/host/update", host)


class IPAMConfigHostAddressAdd(HostCommand):
    command = "ipam config host address add"
    parameters = (
        ("host", String(required=True, completer=get_host_completions)),
        ("address", IPAddress(required=True)),
    )

    async def call(self, host, address, **kwargs):
        host = await self.get_host(host)
        for ip_address in host.ip_address:
            if ip_address == address:
                raise CommandError("Address %s already exists for host %s" % (address, host))
        host.ip_address.append(address)
        await self.client.request("/ipam/config/host/update", host)


class IPAMConfigHostAddressRemove(HostCommand):
    command = "ipam config host address remove"
    parameters = (
        ("host", String(required=True, completer=get_host_completions)),
        ("address", String(required=True, completer=get_host_address_completions)),
    )

    async def call(self, host, address, **kwargs):
        host = await self.get_host(host)
        for i, ip_address in enumerate(host.ip_address):
            if ip_address == address:
                del host.ip_address[i]
                break
        await self.client.request("/ipam/config/host/update", host)


class IPAMCommandSet(CLICommandSet):
    commands = (
        IPAMConfigHostList,
        IPAMConfigHostAdd,
        IPAMConfigHostUpdate,
        IPAMConfigHostRemove,
        IPAMConfigHostAliasAdd,
        IPAMConfigHostAliasRemove,
        IPAMConfigHostAddressAdd,
        IPAMConfigHostAddressRemove,
    )
