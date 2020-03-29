"""
routesia/address/address/commands.py - Routesia address commands
"""
from ipaddress import ip_interface

from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import IPAddress, IPInterface, String, UInt32
from routesia.exceptions import CommandError
from routesia.interface import interface_pb2
from routesia.interface.commands import ConfiguredInterfaceParameter
from routesia.address import address_pb2


class AddressShow(CLICommand):
    command = "address show"
    parameters = (("interface", ConfiguredInterfaceParameter()),)

    async def call(self, interface=None):
        data = await self.client.request("/address/list", None)
        addresses = address_pb2.AddressList.FromString(data)
        if interface:
            interface_addresses = address_pb2.AddressList()
            for address_object in addresses.address:
                if address_object.address.interface == interface:
                    interface_address = interface_addresses.address.add()
                    interface_address.CopyFrom(address_object)
            return interface_addresses
        return addresses


class IPParameter(IPInterface):
    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        interface = kwargs.get("interface", None)
        data = await client.request("/address/config/list", None)
        address_list = address_pb2.AddressConfigList.FromString(data)
        for address in address_list.address:
            if (
                interface is None or interface == address.interface
            ) and address.ip.startswith(suggestion):
                completions.append(address.ip)
        return completions


class AddressConfigList(CLICommand):
    command = "address config list"
    parameters = (
        ("interface", ConfiguredInterfaceParameter()),
        ("ip", IPParameter()),
    )

    async def call(self, interface=None, ip=None):
        data = await self.client.request("/address/config/list", None)
        addresses = address_pb2.AddressConfigList.FromString(data)
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


class AddressConfigAdd(CLICommand):
    command = "address config add"
    parameters = (
        ("interface", ConfiguredInterfaceParameter(required=True)),
        ("ip", IPInterface(required=True)),
        ("peer", IPAddress()),
        ("scope", UInt32()),
    )

    async def call(self, **kwargs):
        address = address_pb2.AddressConfig()
        self.update_message_from_args(address, **kwargs)
        await self.client.request("/address/config/add", address)


class AddressConfigUpdate(CLICommand):
    command = "address config update"
    parameters = (
        ("interface", ConfiguredInterfaceParameter(required=True)),
        ("ip", IPParameter(required=True)),
        ("peer", IPAddress()),
        ("scope", UInt32()),
    )

    async def call(self, interface, ip, **kwargs):
        data = await self.client.request("/address/config/list", None)
        addresses = address_pb2.AddressConfigList.FromString(data)
        address = None
        for address_object in addresses.address:
            if address_object.interface == interface and ip_interface(
                address_object.ip
            ) == ip_interface(ip):
                address = address_object
        if not address:
            raise CommandError("No such address: %s %s" % (interface, ip))
        self.update_message_from_args(address, **kwargs)
        await self.client.request("/address/config/update", address)


class AddressConfigDelete(CLICommand):
    command = "address config delete"
    parameters = (
        ("interface", ConfiguredInterfaceParameter(required=True)),
        ("ip", IPParameter(required=True)),
    )

    async def call(self, interface, ip, **kwargs):
        address = address_pb2.AddressConfig()
        address.interface = interface
        address.ip = ip
        await self.client.request("/address/config/delete", address)


class AddressCommandSet(CLICommandSet):
    commands = (
        AddressShow,
        AddressConfigList,
        AddressConfigAdd,
        AddressConfigUpdate,
        AddressConfigDelete,
    )
