"""
routesia/interface/commands.py - Routesia interface commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String, Bool, UInt32, Int32, ProtobufEnum
from routesia.exceptions import CommandError
from routesia.interface import interface_pb2


class InterfaceShow(CLICommand):
    command = "interface show"
    parameters = (("name", String(max_length=15)),)

    async def call(self, interface=None):
        data = await self.client.request("/interface/list", None)
        interfaces = interface_pb2.InterfaceList.FromString(data)
        if interface:
            for interface_object in interfaces.interface:
                if interface_object.name == interface:
                    return interface_object
            raise CommandError("No such interface: %s" % interface)
        return interfaces

    async def get_name_completions(self, suggestion, **kwargs):
        completions = []
        data = await self.client.request("/interface/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.append(interface.name)
        return completions


class InterfaceConfigNameCompleter:
    async def get_name_completions(self, suggestion, **kwargs):
        completions = []
        data = await self.client.request("/interface/config/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.append(interface.name)
        return completions


class InterfaceConfigList(InterfaceConfigNameCompleter, CLICommand):
    command = "interface config show"
    parameters = (("name", String(max_length=15)),)

    async def call(self, name=None):
        data = await self.client.request("/interface/config/list", None)
        interfaces = interface_pb2.InterfaceConfigList.FromString(data)
        if name:
            for interface_object in interfaces.interface:
                if interface_object.name == name:
                    return interface_object
            raise CommandError("No such interface: %s" % interface)
        return interfaces


class InterfaceParamsCommand(CLICommand):
    parameters = (
        ("name", String(max_length=15, required=True)),
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

    def set_config_from_params(self, config, **kwargs):
        for param_name in kwargs:
            if param_name in self.parameter_map:
                if "." in param_name:
                    sub, field = param_name.split(".")
                    setattr(getattr(config, sub), field, kwargs[param_name])
                else:
                    setattr(config, param_name, kwargs[param_name])


class InterfaceConfigAdd(InterfaceParamsCommand):
    command = "interface config add"

    async def call(self, name, **kwargs):
        interface = interface_pb2.InterfaceConfig()
        interface.name = name
        self.set_config_from_params(interface, **kwargs)
        await self.client.request("/interface/config/add", interface)


class InterfaceConfigUpdate(InterfaceConfigNameCompleter, InterfaceParamsCommand):
    command = "interface config update"

    async def call(self, name, **kwargs):
        data = await self.client.request("/interface/config/list", None)
        interfaces = interface_pb2.InterfaceConfigList.FromString(data)
        interface = None
        for interface_object in interfaces.interface:
            if interface_object.name == name:
                interface = interface_object
        if not interface:
            raise CommandError("No such interface: %s" % name)
        self.set_config_from_params(interface, **kwargs)
        await self.client.request("/interface/config/update", interface)


class InterfaceConfigDelete(InterfaceConfigNameCompleter, CLICommand):
    command = "interface config delete"
    parameters = (
        ("name", String(max_length=15, required=True)),
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
