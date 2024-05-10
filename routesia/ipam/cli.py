"""
routesia/ipam/cli.py - Routesia IPAM commands
"""
from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import EUI
from routesia.rpcclient import RPCClient
from routesia.schema.v1 import ipam_pb2
from routesia.service import Provider


class IPAMCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("ipam")
        self.rpc = rpc

        self.cli.add_argument_completer("hostname", self.complete_hostname)
        self.cli.add_argument_completer("alias", self.complete_alias)
        self.cli.add_argument_completer("address", self.complete_address)

        self.cli.add_command("ipam host list", self.list_hosts)
        self.cli.add_command("ipam host show :hostname", self.get_host)
        self.cli.add_command("ipam config host add :hostname! @hardware-address", self.add_host)
        self.cli.add_command("ipam config host update :hostname @hardware-address", self.update_host)
        self.cli.add_command("ipam config host remove :hostname", self.remove_host)
        self.cli.add_command("ipam config host alias add :hostname :alias!", self.add_alias)
        self.cli.add_command("ipam config host alias remove :hostname :alias", self.remove_alias)
        self.cli.add_command("ipam config host address add :hostname :address!", self.add_address)
        self.cli.add_command("ipam config host address remove :hostname :address", self.remove_address)

    async def complete_hostname(self):
        completions = []
        config = await self.rpc.request("ipam/config/host/list")
        for host in config.host:
            completions.append(host.name)
        return completions

    async def complete_alias(self, hostname: str | None = None):
        completions = []
        if hostname is None:
            return completions
        config = await self.rpc.request("ipam/config/host/list")
        for host in config.host:
            if host.name == hostname:
                break
        else:
            return completions
        for alias in host.alias:
            completions.append(alias)
        return completions

    async def complete_address(self, hostname: str | None = None):
        completions = []
        if hostname is None:
            return completions
        config = await self.rpc.request("ipam/config/host/list")
        for host in config.host:
            if host.name == hostname:
                break
        else:
            return completions
        for ip_address in host.ip_address:
            completions.append(ip_address)
        return completions

    async def list_hosts(self):
        return await self.rpc.request("ipam/config/host/list")

    async def get_host(self, hostname):
        config = await self.rpc.request("ipam/config/host/list")
        for host in config.host:
            if host.name == hostname:
                return host
        raise InvalidArgument("Host %s not found" % hostname)

    async def add_host(self, hostname, hardware_address: EUI = None):
        host = ipam_pb2.Host()
        host.name = hostname
        if hardware_address is not None:
            host.hardware_address = str(hardware_address)
        await self.rpc.request("ipam/config/host/add", host)

    async def update_host(self, hostname, hardware_address: EUI = None):
        host = ipam_pb2.Host()
        host.name = hostname
        if hardware_address is not None:
            host.hardware_address = str(hardware_address)
        await self.rpc.request("ipam/config/host/update", host)

    async def remove_host(self, hostname):
        host = ipam_pb2.Host()
        host.name = hostname
        await self.rpc.request("ipam/config/host/remove", host)

    async def add_alias(self, hostname, alias):
        host = await self.get_host(hostname)
        for alias in host.alias:
            if alias == alias:
                raise InvalidArgument("Alias %s already exists for host %s" % (alias, host))
        host.alias.append(alias)
        await self.rpc.request("ipam/config/host/update", host)

    async def remove_alias(self, hostname, alias):
        host = await self.get_host(hostname)
        for i, alias in enumerate(host.alias):
            if alias == alias:
                del host.alias[i]
                break
        await self.rpc.request("ipam/config/host/update", host)

    async def add_address(self, hostname, address):
        address = str(address)
        host = await self.get_host(hostname)
        for ip_address in host.ip_address:
            if ip_address == address:
                raise InvalidArgument("Address %s already exists for host %s" % (address, host))
        host.ip_address.append(str(address))
        await self.rpc.request("ipam/config/host/update", host)

    async def remove_address(self, hostname, address):
        address = str(address)
        host = await self.get_host(hostname)
        for i, ip_address in enumerate(host.ip_address):
            if ip_address == address:
                del host.ip_address[i]
                break
        await self.rpc.request("ipam/config/host/update", host)
