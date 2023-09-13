"""
routesia/dhcp/server/commands.v4.base.py - Routesia DHCPv4 base server commands
"""
from routesia.cli.command import CLICommand
from routesia.cli.parameters import Bool, IPAddress, String, UInt32
from routesia.exceptions import CommandError
from routesia.interface.commands import ConfiguredInterfaceParameter
from routesia.schema.v1 import dhcpserver_pb2


class DHCPInterfaceParameter(String):
    "Completer using interfaces configured in this module"

    def __init__(self, **kwargs):
        super().__init__(max_length=15, **kwargs)

    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        for interface in config.interface:
            if interface.startswith(suggestion):
                completions.append(interface)
        return completions


class V4ConfigInterfaceList(CLICommand):
    command = "dhcp server v4 config interface list"

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        return "\n".join(config.interface)


class V4ConfigInterfaceAdd(CLICommand):
    command = "dhcp server v4 config interface add"
    parameters = (("interface", ConfiguredInterfaceParameter(required=True)),)

    async def call(self, interface, **kwargs):
        config = dhcpserver_pb2.DHCPv4Server()
        config.interface.append(interface)
        await self.client.request("/dhcp/server/v4/config/interface/add", config)


class V4ConfigInterfaceDelete(CLICommand):
    command = "dhcp server v4 config interface delete"
    parameters = (("interface", DHCPInterfaceParameter(required=True)),)

    async def call(self, interface, **kwargs):
        config = dhcpserver_pb2.DHCPv4Server()
        config.interface.append(interface)
        await self.client.request("/dhcp/server/v4/config/interface/delete", interface)


class V4ConfigGlobalSettingsUpdate(CLICommand):
    command = "dhcp server v4 config global-settings update"
    parameters = (
        ("renew-timer", UInt32()),
        ("rebind-timer", UInt32()),
        ("valid-lifetime", UInt32()),
        ("next-server", IPAddress()),
    )

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        settings = dhcpserver_pb2.DHCPv4Server.FromString(data)
        self.update_message_from_args(settings, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/global_settings/update", settings
        )


class V4ConfigGlobalSettingsShow(CLICommand):
    command = "dhcp server v4 config global-settings show"

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        settings = dhcpserver_pb2.DHCPv4Server.FromString(data)
        lines = [
            f"renew-timer: {settings.renew_timer}",
            f"rebind-timer: {settings.rebind_timer}",
            f"valid-lifetime: {settings.valid_lifetime}",
            f"next-server: {settings.next_server}",
        ]
        return "\n".join(lines)


class V4ConfigOptionDefinitionList(CLICommand):
    command = "dhcp server v4 config option-definition list"

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        return "\n".join([str(d) for d in config.option_definition])


class V4ConfigOptionDefinitionAdd(CLICommand):
    command = "dhcp server v4 config option-definition add"
    parameters = (
        ("name", String(required=True)),
        ("code", UInt32(required=True)),
        ("type", String(required=True)),
        ("space", String()),
        ("array", Bool()),
        ("record-types", String()),
        ("encapsulate", String()),
    )

    async def call(self, **kwargs):
        option_definition = dhcpserver_pb2.OptionDefinition()
        self.update_message_from_args(option_definition, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/option_definition/add", option_definition
        )


class OptionDefinitionParameter(String):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        for option_definition in config.option_definition:
            if option_definition.name.startswith(suggestion):
                completions.append(option_definition.name)
        return completions


class V4ConfigOptionDefinitionUpdate(CLICommand):
    command = "dhcp server v4 config option-definition update"
    parameters = (
        ("name", OptionDefinitionParameter(required=True)),
        ("code", UInt32()),
        ("type", String()),
        ("space", String()),
        ("array", Bool()),
        ("record-types", String()),
        ("encapsulate", String()),
    )

    async def call(self, name, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        option_definition = None
        for od in config.option_definition:
            if od.name == name:
                option_definition = od
                break
        if not option_definition:
            raise CommandError("No such option-definition: %s" % name)
        self.update_message_from_args(option_definition, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/option_definition/update", option_definition
        )


class V4ConfigOptionDefinitionDelete(CLICommand):
    command = "dhcp server v4 config option-definition delete"
    parameters = (("name", OptionDefinitionParameter(required=True)),)

    async def call(self, name, **kwargs):
        option_definition = dhcpserver_pb2.OptionDefinition()
        option_definition.name = name
        await self.client.request(
            "/dhcp/server/v4/config/option_definition/delete", option_definition
        )


class V4ConfigOptionList(CLICommand):
    command = "dhcp server v4 config option list"

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        return "\n".join([str(d) for d in config.option])


class V4ConfigOptionAdd(CLICommand):
    command = "dhcp server v4 config option add"
    parameters = (
        ("name", String()),
        ("code", UInt32()),
        ("data", String(required=True)),
    )

    async def call(self, **kwargs):
        if not ("name" in kwargs or "code" in kwargs):
            raise CommandError("name or code must be specified")

        option = dhcpserver_pb2.OptionData()
        self.update_message_from_args(option, **kwargs)
        await self.client.request("/dhcp/server/v4/config/option/add", option)


class OptionNameParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        for option in config.option:
            if option.name.startswith(suggestion):
                completions.append(option.name)
        return completions


class OptionCodeParameter(UInt32):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        for option in config.option:
            if str(option.code).startswith(suggestion):
                completions.append(str(option.code))
        return completions


class V4ConfigOptionUpdate(CLICommand):
    command = "dhcp server v4 config option update"
    parameters = (
        ("name", OptionNameParameter()),
        ("code", OptionCodeParameter()),
        ("data", String()),
    )

    async def call(self, **kwargs):
        field = None
        if "name" in kwargs:
            field = "name"
        elif "code" in kwargs:
            field = "code"

        if not field:
            raise CommandError("name or code must be specified")

        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        option = None
        for od in config.option:
            if getattr(od, field) == kwargs[field]:
                option = od
                break
        if not option:
            raise CommandError("No such option with %s of %s" % (field, kwargs[field]))

        update_option = dhcpserver_pb2.OptionData()
        update_option.CopyFrom(option)
        self.update_message_from_args(update_option, **kwargs)
        await self.client.request("/dhcp/server/v4/config/option/update", update_option)


class V4ConfigOptionDelete(CLICommand):
    command = "dhcp server v4 config option delete"
    parameters = (
        ("name", OptionNameParameter()),
        ("code", OptionCodeParameter()),
    )

    async def call(self, **kwargs):
        field = None
        if "name" in kwargs:
            field = "name"
        elif "code" in kwargs:
            field = "code"

        if not field:
            raise CommandError("name or code must be specified")

        option = dhcpserver_pb2.OptionData()
        setattr(option, field, kwargs[field])
        await self.client.request("/dhcp/server/v4/config/option/delete", option)
