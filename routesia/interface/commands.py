"""
routesia/interface/commands.py - Routesia interface commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String, Bool, UInt32, Int32, ProtobufEnum
from routesia.exceptions import CommandError
from routesia.interface import interface_pb2


class InterfaceParameter(String):
    "Completer using interfaces found on the system"

    def __init__(self, **kwargs):
        super().__init__(max_length=15, **kwargs)

    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        data = await client.request("/interface/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.append(interface.name)
        return completions


class ConfiguredInterfaceParameter(String):
    "Completer using configured interfaces"

    def __init__(self, **kwargs):
        super().__init__(max_length=15, **kwargs)

    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        data = await client.request("/interface/config/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.append(interface.name)
        return completions


class InterfaceShow(CLICommand):
    command = "interface show"
    parameters = (("name", InterfaceParameter()),)

    async def call(self, interface=None):
        data = await self.client.request("/interface/list", None)
        interfaces = interface_pb2.InterfaceList.FromString(data)
        if interface:
            for interface_object in interfaces.interface:
                if interface_object.name == interface:
                    return interface_object
            raise CommandError("No such interface: %s" % interface)
        return interfaces


class InterfaceConfigList(CLICommand):
    command = "interface config list"
    parameters = (("name", ConfiguredInterfaceParameter()),)

    async def call(self, name=None):
        data = await self.client.request("/interface/config/list", None)
        interfaces = interface_pb2.InterfaceConfigList.FromString(data)
        if name:
            for interface_object in interfaces.interface:
                if interface_object.name == name:
                    return interface_object
            raise CommandError("No such interface: %s" % interface)
        return interfaces


interface_optional_parameters = (
    ("type", ProtobufEnum(interface_pb2.InterfaceType)),
    ("link.up", Bool()),
    ("link.noarp", Bool()),
    ("link.txqueuelen", UInt32()),
    ("link.mtu", UInt32()),
    ("link.address", String()),
    ("link.broadcast", String()),
    ("link.addrgenmode", ProtobufEnum(interface_pb2.InterfaceLink.AddrGenMode)),
    ("link.token", String()),
    ("bridge.ageing_time", UInt32()),
    ("bridge.forward_delay", UInt32()),
    ("bridge.hello_time", UInt32()),
    ("bridge.max_age", UInt32()),
    ("bridge.stp", Bool()),
    ("bridge.priority", Int32()),
    ("bridge.vlan_filtering", Bool()),
    ("bridge.default_pvid", Int32()),
)


class InterfaceConfigAdd(CLICommand):
    command = "interface config add"
    parameters = (
        ("name", String(max_length=15, required=True)),
    ) + interface_optional_parameters

    async def call(self, name, **kwargs):
        interface = interface_pb2.InterfaceConfig()
        interface.name = name
        self.update_message_from_args(interface, **kwargs)
        if interface.type == interface_pb2.UNDEFINED:
            # If type is not given, default to ETHERNET
            interface.type = interface_pb2.ETHERNET
        await self.client.request("/interface/config/add", interface)


class InterfaceConfigUpdate(CLICommand):
    command = "interface config update"
    parameters = (
        ("name", ConfiguredInterfaceParameter(required=True)),
    ) + interface_optional_parameters

    async def call(self, name, **kwargs):
        data = await self.client.request("/interface/config/list", None)
        interfaces = interface_pb2.InterfaceConfigList.FromString(data)
        interface = None
        for interface_object in interfaces.interface:
            if interface_object.name == name:
                interface = interface_object
        if not interface:
            raise CommandError("No such interface: %s" % name)
        self.update_message_from_args(interface, **kwargs)
        await self.client.request("/interface/config/update", interface)


class InterfaceConfigDelete(CLICommand):
    command = "interface config delete"
    parameters = (
        ("name", ConfiguredInterfaceParameter(required=True)),
    )

    async def call(self, name, **kwargs):
        interface = interface_pb2.InterfaceConfig()
        interface.name = name
        await self.client.request("/interface/config/delete", interface)


class InterfaceCommandSet(CLICommandSet):
    commands = (
        InterfaceShow,
        InterfaceConfigList,
        InterfaceConfigAdd,
        InterfaceConfigUpdate,
        InterfaceConfigDelete,
    )