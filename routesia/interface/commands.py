"""
routesia/interface/commands.py - Routesia interface commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String, Bool, UInt32, Int32, ProtobufEnum
from routesia.exceptions import CommandError
from routesia.interface import interface_pb2


class ShowInterfaces(CLICommand):
    command = "interface show"
    parameters = (
        ('interface', String(max_length=15)),
    )

    async def call(self, interface=None):
        data = await self.client.request("/interface/list", None)
        interfaces = interface_pb2.InterfaceList.FromString(data)
        if interface:
            for interface_object in interfaces.interface:
                if interface_object.name == interface:
                    return interface_object
            raise CommandError("No such interface: %s" % interface)
        return interfaces

    async def get_interface_completions(self, suggestion, **kwargs):
        completions = []
        data = await self.client.request("/interface/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.append(interface.name)
        return completions


class AddInterface(CLICommand):
    command = "interface add"
    parameters = (
        ('name', String(max_length=15, required=True)),
        ('type', ProtobufEnum(interface_pb2.InterfaceType)),
        ('link.up', Bool()),
        ('link.noarp', Bool()),
        ('link.txqueuelen', UInt32()),
        ('link.mtu', UInt32()),
        ('link.address', String()),
        ('link.broadcast', String()),
        ('link.addrgenmode', ProtobufEnum(interface_pb2.InterfaceLink.AddrGenMode)),
        ('link.token', String()),
        ('bridge.ageing_time', UInt32()),
        ('bridge.forward_delay', UInt32()),
        ('bridge.hello_time', UInt32()),
        ('bridge.max_age', UInt32()),
        ('bridge.stp', Bool()),
        ('bridge.priority', Int32()),
        ('bridge.vlan_filtering', Bool()),
        ('bridge.default_pvid', Int32()),
    )

    async def call(self, **kwargs):
        interface = interface_pb2.InterfaceConfig()
        interface.name = kwargs['name']
        if 'type' in kwargs:
            interface.type = kwargs['type']
        await self.client.request("/interface/config/add", interface)


class InterfaceCommandSet(CLICommandSet):
    commands = (
        ShowInterfaces,
        AddInterface,
    )
