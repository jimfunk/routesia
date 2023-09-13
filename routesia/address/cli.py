"""
routesia/address/cli.py - Routesia address CLI
"""
from ipaddress import ip_interface

from routesia.cli import CLI
from routesia.rpcclient import RPCClient
from routesia.service import Provider
from routesia.schema.v1 import address_pb2



# from routesia.cli.parameters import IPAddress, IPInterface, UInt32
# from routesia.interface.commands import ConfiguredInterfaceParameter


class AddressCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli
        self.rpc = rpc

        self.cli.add_argument_completer("interface", self.complete_interfaces)
        self.cli.add_argument_completer("ip", self.complete_ips)

        self.cli.add_command("address show", self.show_addresses)
        self.cli.add_command("address show @interface", self.show_addresses)
        self.cli.add_command("address config list", self.show_address_configs)
        # self.cli.add_command("address config list @interface @ip", self.show_address_configs)
        self.cli.add_command("address config list :interface", self.show_address_configs)
        self.cli.add_command("address config list :ip", self.show_address_configs)

    async def complete_interfaces(self, **args):
        interfaces = []
        interface_list = await self.rpc.request("interface/list", None)
        for interface in interface_list.interface:
            interfaces.append(interface.name)
        return interfaces

    async def complete_ips(self, **args):
        ips = []
        address_list = await self.rpc.request("address/config/list", None)
        for address in address_list.address:
            ips.append(address.ip)
        return ips

    async def show_addresses(self, interface=None):
        addresses = await self.rpc.request("address/list", None)
        if interface:
            interface_addresses = address_pb2.AddressList()
            for address_object in addresses.address:
                if address_object.address.interface == interface:
                    interface_address = interface_addresses.address.add()
                    interface_address.CopyFrom(address_object)
            return interface_addresses
        return addresses

    async def show_address_configs(self, interface=None, ip=None):
        addresses = await self.rpc.request("address/config/list", None)
        if interface:
            interface_addresses = address_pb2.AddressConfigList()
            for address_config in addresses.address:
                if address_config.interface == interface:
                    address = interface_addresses.address.add()
                    address.CopyFrom(address_config)
            addresses = interface_addresses
        if ip:
            ip_addresses = address_pb2.AddressConfigList()
            for address_config in addresses.address:
                if address_config.ip == ip:
                    address = ip_addresses.address.add()
                    address.CopyFrom(address_config)
            addresses = ip_addresses
        return addresses


# class AddressConfigList(CLICommand):
#     command = "address config list"
#     parameters = (
#         ("interface", ConfiguredInterfaceParameter()),
#         ("ip", IPParameter()),
#     )

#     async def call(self, interface=None, ip=None):

# class IPParameter(IPInterface):
#     async def get_completions(self, client, suggestion, **kwargs):
#         completions = []
#         interface = kwargs.get("interface", None)
#         data = await client.request("address/config/list", None)
#         address_list = address_pb2.AddressConfigList.FromString(data)
#         for address in address_list.address:
#             if (
#                 interface is None or interface == address.interface
#             ) and address.ip.startswith(suggestion):
#                 completions.append(address.ip)
#         return completions




# class AddressConfigAdd(CLICommand):
#     command = "address config add"
#     parameters = (
#         ("interface", ConfiguredInterfaceParameter(required=True)),
#         ("ip", IPInterface(required=True)),
#         ("peer", IPAddress()),
#         ("scope", UInt32()),
#     )

#     async def call(self, **kwargs):
#         address = address_pb2.AddressConfig()
#         self.update_message_from_args(address, **kwargs)
#         await self.rpc.request("address/config/add", address)


# class AddressConfigUpdate(CLICommand):
#     command = "address config update"
#     parameters = (
#         ("interface", ConfiguredInterfaceParameter(required=True)),
#         ("ip", IPParameter(required=True)),
#         ("peer", IPAddress()),
#         ("scope", UInt32()),
#     )

#     async def call(self, interface, ip, **kwargs):
#         data = await self.rpc.request("address/config/list", None)
#         addresses = address_pb2.AddressConfigList.FromString(data)
#         address = None
#         for address_object in addresses.address:
#             if address_object.interface == interface and ip_interface(
#                 address_object.ip
#             ) == ip_interface(ip):
#                 address = address_object
#         if not address:
#             raise CommandError("No such address: %s %s" % (interface, ip))
#         self.update_message_from_args(address, **kwargs)
#         await self.rpc.request("address/config/update", address)


# class AddressConfigDelete(CLICommand):
#     command = "address config delete"
#     parameters = (
#         ("interface", ConfiguredInterfaceParameter(required=True)),
#         ("ip", IPParameter(required=True)),
#     )

#     async def call(self, interface, ip, **kwargs):
#         address = address_pb2.AddressConfig()
#         address.interface = interface
#         address.ip = ip
#         await self.rpc.request("address/config/delete", address)


# class AddressCommandSet(CLICommandSet):
#     commands = (
#         AddressShow,
#         AddressConfigList,
#         AddressConfigAdd,
#         AddressConfigUpdate,
#         AddressConfigDelete,
#     )
