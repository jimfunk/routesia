"""
routesia/address/cli.py - Routesia address CLI
"""
from ipaddress import ip_interface, IPv4Interface, IPv6Interface

from routesia.cli import CLI, InvalidArgument
from routesia.rpcclient import RPCClient
from routesia.service import Provider
from routesia.schema.v2 import address_pb2


class AddressCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("address")
        self.rpc = rpc

        self.cli.add_argument_completer("interface", self.complete_interfaces)
        self.cli.add_argument_completer("ip", self.complete_ips)

        self.cli.add_command("address show", self.show_addresses)
        self.cli.add_command("address show @interface", self.show_addresses)
        self.cli.add_command("address config list", self.show_address_configs)
        self.cli.add_command("address config list :interface", self.show_address_configs)
        self.cli.add_command("address config add :interface :ip @peer @scope", self.add_address_config)
        self.cli.add_command("address config update :interface :ip @peer @scope", self.update_address_config)
        self.cli.add_command("address config delete :interface :ip", self.delete_address_config)

    async def complete_interfaces(self):
        interfaces = []
        interface_list = await self.rpc.request("interface/list")
        for interface in interface_list.interface:
            interfaces.append(interface.name)
        return interfaces

    async def complete_ips(self):
        ips = []
        address_list = await self.rpc.request("address/config/list")
        for address in address_list.address:
            ips.append(address.ip)
        return ips

    async def show_addresses(self, interface: str = None):
        addresses = await self.rpc.request("address/list")
        if interface:
            interface_addresses = address_pb2.AddressList()
            for address_object in addresses.address:
                if address_object.address.interface == interface:
                    interface_address = interface_addresses.address.add()
                    interface_address.CopyFrom(address_object)
            return interface_addresses
        return addresses

    async def show_address_configs(self, interface: str = None):
        addresses = await self.rpc.request("address/config/list")
        if interface:
            interface_addresses = address_pb2.AddressConfigList()
            for address_config in addresses.address:
                if address_config.interface == interface:
                    address = interface_addresses.address.add()
                    address.CopyFrom(address_config)
            addresses = interface_addresses
        return addresses

    async def add_address_config(
        self,
        interface: str,
        ip: IPv4Interface | IPv6Interface,
        peer: IPv4Interface | IPv6Interface = None,
        scope=None,
    ):
        address = address_pb2.AddressConfig()
        address.interface = interface
        address.ip = str(ip)
        if peer is not None:
            address.peer = peer
        if scope is not None:

            address.scope = int(scope)
        await self.rpc.request("address/config/add", address)

    async def get_address(self, interface: str, ip: IPv4Interface | IPv6Interface):
        addresses = await self.rpc.request("address/config/list")
        address = None

        for address_object in addresses.address:
            if address_object.interface == interface and ip_interface(
                address_object.ip
            ) == ip_interface(ip):
                address = address_object

        if not address:
            raise InvalidArgument("No such address: %s %s" % (interface, ip))

        return address

    async def update_address_config(
        self,
        interface: str,
        ip: IPv4Interface | IPv6Interface,
        peer: IPv4Interface | IPv6Interface = None,
        scope=None,
    ):
        address = await self.get_address(interface, ip)

        if peer is not None:
            address.peer = peer
        if scope is not None:
            address.scope = int(scope)

        await self.rpc.request("address/config/update", address)

    async def delete_address_config(
        self,
        interface: str,
        ip: IPv4Interface | IPv6Interface,
    ):
        address = address_pb2.AddressConfig()
        address.interface = interface
        address.ip = ip
        await self.rpc.request("address/config/delete", address)
