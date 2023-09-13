"""
routesia/dhcp/server/commands/v4/client_class.py - Routesia DHCPv4 server client class commands
"""
from routesia.cli.command import CLICommand
from routesia.cli.parameters import String, UInt32, Bool
from routesia.exceptions import CommandError
from routesia.schema.v1 import dhcpserver_pb2


class V4ConfigClientClassList(CLICommand):
    command = "dhcp server v4 config client-class list"

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        return "\n".join([str(d) for d in config.client_class])


class V4ConfigClientClassAdd(CLICommand):
    command = "dhcp server v4 config client-class add"
    parameters = (
        ("name", String(required=True)),
        ("test", String(required=True)),
        ("next-server", String()),
    )

    async def call(self, **kwargs):
        client_class = dhcpserver_pb2.ClientClass()
        self.update_message_from_args(client_class, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/client_class/add", client_class
        )


class ClientClassParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        for client_class in config.client_class:
            if client_class.name.startswith(suggestion):
                completions.append(client_class.name)
        return completions


class V4ConfigClientClassUpdate(CLICommand):
    command = "dhcp server v4 config client-class update"
    parameters = (
        ("name", ClientClassParameter(required=True)),
        ("test", String()),
        ("next-server", String()),
    )

    async def call(self, name, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        client_class = None
        for cc in config.client_class:
            if cc.name == name:
                client_class = cc
                break
        if not client_class:
            raise CommandError("No such client-class: %s" % name)
        self.update_message_from_args(client_class, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/client_class/update", client_class
        )


class V4ConfigClientClassDelete(CLICommand):
    command = "dhcp server v4 config client-class delete"
    parameters = (("name", ClientClassParameter(required=True)),)

    async def call(self, name, **kwargs):
        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = name
        await self.client.request(
            "/dhcp/server/v4/config/client_class/delete", client_class
        )


class V4ConfigClientClassOptionDefinitionList(CLICommand):
    command = "dhcp server v4 config client-class option-definition list"
    parameters = (("client-class", ClientClassParameter(required=True)),)

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        client_class = None
        for cc in config.client_class:
            if cc.name == kwargs["client-class"]:
                client_class = cc
                break
        if not client_class:
            raise CommandError("No such client-class: %s" % kwargs["client-class"])

        return "\n".join([str(d) for d in client_class.option_definition])


class V4ConfigClientClassOptionDefinitionAdd(CLICommand):
    command = "dhcp server v4 config client-class option-definition add"
    parameters = (
        ("client-class", ClientClassParameter(required=True)),
        ("name", String(required=True)),
        ("code", UInt32(required=True)),
        ("type", String(required=True)),
        ("space", String()),
        ("array", Bool()),
        ("record-types", String()),
        ("encapsulate", String()),
    )

    async def call(self, **kwargs):
        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = kwargs["client-class"]
        option_definition = client_class.option_definition.add()
        self.update_message_from_args(option_definition, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/client_class/option_definition/add", client_class
        )


class ClientClassOptionDefinitionParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        client_class_name = kwargs.get("client-class", None)
        client_class = None

        for cc in config.client_class:
            if cc.name == client_class_name:
                client_class = cc
                break
        else:
            return []

        for option_definition in client_class.option_definition:
            if option_definition.name.startswith(suggestion):
                completions.append(option_definition.name)
        return completions


class V4ConfigClientClassOptionDefinitionUpdate(CLICommand):
    command = "dhcp server v4 config client-class option-definition update"
    parameters = (
        ("client-class", ClientClassParameter(required=True)),
        ("name", ClientClassOptionDefinitionParameter(required=True)),
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

        client_class = None
        for cc in config.client_class:
            if cc.name == kwargs["client-class"]:
                client_class = cc
                break
        if not client_class:
            raise CommandError("No such client-class: %s" % kwargs["client-class"])

        option_definition = None
        for od in client_class.option_definition:
            if od.name == name:
                option_definition = od
                break
        if not option_definition:
            raise CommandError("No such option-definition: %s" % name)

        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = kwargs["client-class"]
        updated_option_definition = client_class.option_definition.add()
        updated_option_definition.CopyFrom(option_definition)
        self.update_message_from_args(updated_option_definition, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/client_class/option_definition/update", client_class
        )


class V4ConfigClientClassOptionDefinitionDelete(CLICommand):
    command = "dhcp server v4 config client-class option-definition delete"
    parameters = (
        ("client-class", ClientClassParameter(required=True)),
        ("name", ClientClassOptionDefinitionParameter(required=True)),
    )

    async def call(self, name, **kwargs):
        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = kwargs["client-class"]
        option_definition = client_class.option_definition.add()
        option_definition.name = name
        await self.client.request(
            "/dhcp/server/v4/config/client_class/option_definition/delete", client_class
        )


class V4ConfigClientClassOptionList(CLICommand):
    command = "dhcp server v4 config client-class option list"
    parameters = (("client-class", ClientClassParameter(required=True)),)

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        client_class = None
        for cc in config.client_class:
            if cc.name == kwargs["client-class"]:
                client_class = cc
                break
        if not client_class:
            raise CommandError("No such client-class: %s" % kwargs["client-class"])

        return "\n".join([str(d) for d in client_class.option])


class V4ConfigClientClassOptionAdd(CLICommand):
    command = "dhcp server v4 config client-class option add"
    parameters = (
        ("client-class", ClientClassParameter(required=True)),
        ("name", String()),
        ("code", UInt32()),
        ("data", String(required=True)),
    )

    async def call(self, **kwargs):
        if not ("name" in kwargs or "code" in kwargs):
            raise CommandError("name or code must be specified")

        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = kwargs["client-class"]
        option = client_class.option.add()
        self.update_message_from_args(option, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/client_class/option/add", client_class
        )


class ClientClassOptionNameParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        client_class_name = kwargs.get("client-class", None)
        client_class = None

        for cc in config.client_class:
            if cc.name == client_class_name:
                client_class = cc
                break
        else:
            return []

        for option in client_class.option:
            if option.name.startswith(suggestion):
                completions.append(option.name)
        return completions


class ClientClassOptionCodeParameter(UInt32):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        client_class_name = kwargs.get("client-class", None)
        client_class = None

        for cc in config.client_class:
            if cc.name == client_class_name:
                client_class = cc
                break
        else:
            return []

        for option in client_class.option:
            if str(option.code).startswith(suggestion):
                completions.append(str(option.code))
        return completions


class V4ConfigClientClassOptionUpdate(CLICommand):
    command = "dhcp server v4 config client-class option update"
    parameters = (
        ("client-class", ClientClassParameter(required=True)),
        ("name", ClientClassOptionNameParameter()),
        ("code", ClientClassOptionCodeParameter()),
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

        client_class = None
        for cc in config.client_class:
            if cc.name == kwargs["client-class"]:
                client_class = cc
                break
        if not client_class:
            raise CommandError("No such client-class: %s" % kwargs["client-class"])

        option = None
        for od in client_class.option:
            if getattr(od, field) == kwargs[field]:
                option = od
                break
        if not option:
            raise CommandError("No such option with %s of %s" % (field, kwargs[field]))

        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = kwargs["client-class"]
        option = client_class.option.add()
        option.CopyFrom(option)
        self.update_message_from_args(option, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/client_class/option/update", client_class
        )


class V4ConfigClientClassOptionDelete(CLICommand):
    command = "dhcp server v4 config client-class option delete"
    parameters = (
        ("client-class", ClientClassParameter(required=True)),
        ("name", ClientClassOptionNameParameter()),
        ("code", ClientClassOptionCodeParameter()),
    )

    async def call(self, **kwargs):
        field = None
        if "name" in kwargs:
            field = "name"
        elif "code" in kwargs:
            field = "code"

        if not field:
            raise CommandError("name or code must be specified")

        client_class = dhcpserver_pb2.ClientClass()
        client_class.name = kwargs["client-class"]
        option = client_class.option.add()
        setattr(option, field, kwargs[field])
        await self.client.request(
            "/dhcp/server/v4/config/client_class/option/delete", client_class
        )
