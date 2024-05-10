"""
routesia/dhcp/server/cli.py - Routesia DHCPv4 server commands
"""

from ipaddress import IPv4Address, IPv4Network, ip_address
import re

from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import EUI, UInt32
from routesia.rpcclient import RPCClient
from routesia.service import Provider
from routesia.schema.v1 import dhcp_server_pb2


class PoolDefinition:
    IP_RE = r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    POOL_RE = re.compile("^%s-%s$" % (IP_RE, IP_RE))

    def __init__(self, value: str):
        if not self.POOL_RE.fullmatch(value):
            raise ValueError(
                "pool definition does not match expected <start_address>-<end_address>"
            )
        start, end = value.split("-")
        self.start_address = ip_address(start)
        self.end_address = ip_address(end)
        if self.start_address > self.end_address:
            raise ValueError("Start address must be <= end address")

    def __str__(self):
        return f"{self.start_address}-{self.end_address}"


class DHCPServerCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("dhcp-server")
        self.rpc = rpc

        self.cli.add_argument_completer("interface", self.complete_interfaces)
        self.cli.add_argument_completer(
            "option-definition-name", self.complete_option_definition_names
        )
        self.cli.add_argument_completer("option-name", self.complete_option_names)
        self.cli.add_argument_completer("option-code", self.complete_option_codes)
        self.cli.add_argument_completer("client-class", self.complete_client_classes)
        self.cli.add_argument_completer(
            "client-class-option-definition",
            self.complete_client_class_option_definitions,
        )
        self.cli.add_argument_completer(
            "client-class-option-name", self.complete_client_class_option_names
        )
        self.cli.add_argument_completer(
            "client-class-option-code", self.complete_client_class_option_codes
        )
        self.cli.add_argument_completer("subnet", self.complete_subnets)
        self.cli.add_argument_completer("pool", self.complete_pools)
        self.cli.add_argument_completer(
            "subnet-option-name", self.complete_subnet_option_names
        )
        self.cli.add_argument_completer(
            "subnet-option-code", self.complete_subnet_option_codes
        )
        self.cli.add_argument_completer(
            "subnet-hardware-reservation", self.complete_subnet_hardware_reservations
        )
        self.cli.add_argument_completer(
            "subnet-relay-address", self.complete_subnet_relay_addresses
        )

        self.cli.add_command("dhcp server v4 config show", self.show_config)
        self.cli.add_command(
            "dhcp server v4 config interface list", self.list_interfaces
        )
        self.cli.add_command(
            "dhcp server v4 config interface add :interface", self.add_interface
        )
        self.cli.add_command(
            "dhcp server v4 config interface delete :interface", self.delete_interface
        )
        self.cli.add_command(
            "dhcp server v4 config global-settings update @renew-timer @rebind-timer @valid-lifetime @next-server",
            self.update_global_settings,
        )
        self.cli.add_command(
            "dhcp server v4 config global-settings show", self.show_global_settings
        )
        self.cli.add_command(
            "dhcp server v4 config option-definition list", self.list_option_definitions
        )
        self.cli.add_command(
            "dhcp server v4 config option-definition add :name :code :type @space @array @record-types @encapsulate",
            self.add_option_definition,
        )
        self.cli.add_command(
            "dhcp server v4 config option-definition update :option-name @option-code @type @space @array @record-types @encapsulate",
            self.update_option_definition,
        )
        self.cli.add_command(
            "dhcp server v4 config option-definition delete :option-name",
            self.delete_option_definition,
        )
        self.cli.add_command("dhcp server v4 config option list", self.list_options)
        self.cli.add_command(
            "dhcp server v4 config option add @name @code @data", self.add_option
        )
        self.cli.add_command(
            "dhcp server v4 config option update @option-name @option-code @data",
            self.update_option,
        )
        self.cli.add_command(
            "dhcp server v4 config option delete @option-name @option-code",
            self.delete_option,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class list", self.list_client_classes
        )
        self.cli.add_command(
            "dhcp server v4 config client-class add :name :test @next-server",
            self.add_client_class,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class update :client-class @test @next-server",
            self.update_client_class,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class delete :client-class",
            self.delete_client_class,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option-definition list :client-class",
            self.list_client_class_option_definitions,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option-definition add :client-class :name :code :type @space @array @record-types @encapsulate",
            self.add_client_class_option_definition,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option-definition update :client-class :client-class-option-definition @code @type @space @array @record-types @encapsulate",
            self.update_client_class_option_definition,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option-definition delete :client-class :client-class-option-definition",
            self.delete_client_class_option_definition,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option list :client-class",
            self.list_client_class_options,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option add :client-class @name @code @data",
            self.add_client_class_option,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option update :client-class @client-class-option-name @client-class-option-code @data",
            self.update_client_class_option,
        )
        self.cli.add_command(
            "dhcp server v4 config client-class option delete :client-class @client-class-option-name @client-class-option-code",
            self.delete_client_class_option,
        )
        self.cli.add_command("dhcp server v4 config subnet list", self.list_subnets)
        self.cli.add_command(
            "dhcp server v4 config subnet add :address @use-ipam @next-server",
            self.add_subnet,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet update :subnet @use-ipam @next-server",
            self.update_subnet,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet delete :subnet", self.delete_subnet
        )
        self.cli.add_command(
            "dhcp server v4 config subnet pool add :subnet :pool-definition",
            self.add_pool,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet pool delete :subnet :pool", self.delete_pool
        )
        self.cli.add_command(
            "dhcp server v4 config subnet option list :subnet", self.list_subnet_options
        )
        self.cli.add_command(
            "dhcp server v4 config subnet option add :subnet @name @code @data",
            self.add_subnet_option,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet option update :subnet @subnet-option-name @subnet-option-code @data",
            self.update_subnet_option,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet option delete :subnet @subnet-option-name @subnet-option-code",
            self.delete_subnet_option,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet reservation list :subnet",
            self.list_subnet_reservations,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet reservation add :subnet :hardware-address :ip_address",
            self.add_subnet_reservation,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet reservation update :subnet :subnet-hardware-reservation :ip_address",
            self.update_subnet_reservation,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet reservation delete :subnet :subnet-hardware-reservation",
            self.delete_subnet_reservation,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet relay-address add :subnet :ip-address",
            self.add_relay_address,
        )
        self.cli.add_command(
            "dhcp server v4 config subnet relay-address delete :subnet :relay-address",
            self.delete_relay_address,
        )
        self.cli.add_command("dhcp server v4 leases :subnet", self.show_subnet_leases)

    async def complete_interfaces(self):
        interfaces = []
        interface_list = await self.rpc.request("interface/list")
        for interface in interface_list.interface:
            interfaces.append(interface.name)
        return interfaces

    async def complete_option_definition_names(self):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        completions = []
        for option_definition in config.option_definition:
            completions.append(option_definition.name)
        return completions

    async def complete_option_names(self):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        completions = []
        for option in config.option:
            completions.append(option.name)
        return completions

    async def complete_option_codes(self):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        completions = []
        for option in config.option:
            completions.append(str(option.code))
        return completions

    async def complete_client_classes(self):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        for client_class in config.client_class:
            completions.append(client_class.name)
        return completions

    async def complete_client_class_option_definitions(self, client_class: str = None):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        if client_class is None:
            return completions
        for client_class_item in config.client_class:
            if client_class_item.name == client_class:
                for option_definition in client_class_item.option_definition:
                    completions.append(option_definition.name)
                break
        return completions

    async def complete_client_class_option_names(self, client_class: str = None):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        if client_class is None:
            return completions
        for client_class_item in config.client_class:
            if client_class_item.name == client_class:
                for option in client_class.option:
                    completions.append(option.name)
                break
        return completions

    async def complete_client_class_option_codes(self, client_class: str = None):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        if client_class is None:
            return completions
        for client_class_item in config.client_class:
            if client_class_item.name == client_class:
                for option in client_class.option:
                    completions.append(str(option.code))
                break
        return completions

    async def complete_subnets(self):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        for subnet in config.subnet:
            completions.append(subnet.address)
        return completions

    async def complete_pools(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        subnet_address = str(subnet)
        for subnet in config.subnet:
            if subnet.address == subnet_address:
                for pool in subnet.pool:
                    completions.append(pool)
                break
        return completions

    async def complete_subnet_option_names(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        subnet_address = str(subnet)
        for subnet in config.subnet:
            if subnet.address == subnet_address:
                for option in subnet.option:
                    completions.append(option.name)
                break
        return completions

    async def complete_subnet_option_codes(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        subnet_address = str(subnet)
        for subnet in config.subnet:
            if subnet.address == subnet_address:
                for option in subnet.option:
                    completions.append(str(option.code))
                break
        return completions

    async def complete_subnet_hardware_reservations(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        subnet_address = str(subnet)
        for sn in config.subnet:
            if sn.address == subnet_address:
                for reservation in sn.reservation:
                    completions.append(reservation.hardware_address)
                break
        return completions

    async def complete_subnet_relay_addresses(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        completions = []
        subnet_address = str(subnet)
        for subnet in config.subnet:
            if subnet.address == subnet_address:
                for relay_address in subnet.relay_address:
                    completions.append(relay_address)
                break
        return completions

    async def show_config(self):
        return await self.rpc.request("dhcp/server/v4/config/get")

    async def list_interfaces(self):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        return "\n".join(config.interface)

    async def add_interface(self, interface):
        config = dhcp_server_pb2.DHCPv4Server()
        config.interface.append(interface)
        await self.rpc.request("dhcp/server/v4/config/interface/add", config)

    async def delete_interface(self, interface):
        config = dhcp_server_pb2.DHCPv4Server()
        config.interface.append(interface)
        await self.rpc.request("dhcp/server/v4/config/interface/delete", config)

    async def update_global_settings(
        self,
        renew_timer: UInt32 = None,
        rebind_timer: UInt32 = None,
        valid_lifetime: UInt32 = None,
        next_server: IPv4Address = None,
    ):
        settings = await self.rpc.request("dhcp/server/v4/config/get")
        if renew_timer is not None:
            settings.renew_timer = renew_timer
        if rebind_timer is not None:
            settings.rebind_timer = rebind_timer
        if valid_lifetime is not None:
            settings.valid_lifetime = valid_lifetime
        if next_server is not None:
            settings.next_server = next_server
        await self.rpc.request("dhcp/server/v4/config/global_settings/update", settings)

    async def show_global_settings(self):
        settings = await self.rpc.request("dhcp/server/v4/config/get")
        lines = [
            f"renew-timer: {settings.renew_timer}",
            f"rebind-timer: {settings.rebind_timer}",
            f"valid-lifetime: {settings.valid_lifetime}",
            f"next-server: {settings.next_server}",
        ]
        return "\n".join(lines)

    async def list_option_definitions(self):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        return "\n".join([str(d) for d in config.option_definition])

    async def add_option_definition(
        self,
        name: str,
        code: UInt32,
        type: str,
        space: str = "",
        array: bool = None,
        record_types: str = "",
        encapsulate: str = "",
    ):
        option_definition = dhcp_server_pb2.OptionDefinition()
        option_definition.name = name
        option_definition.code = code
        option_definition.type = type
        if space is not None:
            option_definition.space = space
        if array is not None:
            option_definition.array = array
        if record_types is not None:
            option_definition.record_types = record_types
        if encapsulate is not None:
            option_definition.encapsulate = encapsulate
        await self.rpc.request(
            "dhcp/server/v4/config/option_definition/add", option_definition
        )

    async def update_option_definition(
        self,
        option_name: str,
        option_code: UInt32 = None,
        type: str = None,
        space: str = None,
        array: bool = None,
        record_types: str = None,
        encapsulate: str = None,
    ):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        option_definition = None
        for od in config.option_definition:
            if od.name == option_name:
                option_definition = od
                break
        if not option_definition:
            raise InvalidArgument("No such option-definition: %s" % option_name)
        if option_code is not None:
            option_definition.code = option_code
        if type is not None:
            option_definition.type = type
        if space is not None:
            option_definition.space = space
        if array is not None:
            option_definition.array = array
        if record_types is not None:
            option_definition.record_types = record_types
        if encapsulate is not None:
            option_definition.encapsulate = encapsulate
        await self.rpc.request(
            "dhcp/server/v4/config/option_definition/update", option_definition
        )

    async def delete_option_definition(self, option_name: str):
        option_definition = dhcp_server_pb2.OptionDefinition()
        option_definition.name = option_name
        await self.rpc.request(
            "dhcp/server/v4/config/option_definition/delete", option_definition
        )

    async def list_options(self):
        config = await self.rpc.request("dhcp/server/v4/config/get")
        return "\n".join([str(d) for d in config.option])

    async def add_option(
        self,
        name: str | None = None,
        code: UInt32 | None = None,
        data: str | None = None,
    ):
        if (name is None and code is None) or (name is not None and code is not None):
            raise InvalidArgument("one of name or code must be specified")
        if data is None:
            raise InvalidArgument("data must be specified")

        option = dhcp_server_pb2.OptionData()
        if name is not None:
            option.name = name
        if code is not None:
            option.code = code
        option.data = data

        await self.rpc.request("dhcp/server/v4/config/option/add", option)

    async def update_option(
        self,
        option_name: str | None = None,
        option_code: UInt32 | None = None,
        data: str | None = None,
    ):
        if (option_name is None and option_code is None) or (
            option_name is not None and option_code is not None
        ):
            raise InvalidArgument("one of option_name or option_code must be specified")
        if data is None:
            raise InvalidArgument("data must be specified")

        config = await self.rpc.request("dhcp/server/v4/config/get")

        option = None
        for od in config.option:
            if option_name is not None and od.name == option_name:
                option = od
                break
            if option_code is not None and od.code == option_code:
                option = od
                break
        if not option:
            raise InvalidArgument("No matching option found")

        update_option = dhcp_server_pb2.OptionData()
        update_option.CopyFrom(option)
        update_option.data = data
        await self.rpc.request("dhcp/server/v4/config/option/update", update_option)

    async def delete_option(
        self,
        option_name: str | None = None,
        option_code: UInt32 | None = None,
    ):
        if (option_name is None and option_code is None) or (
            option_name is not None and option_code is not None
        ):
            raise InvalidArgument("one of option_name or option_code must be specified")

        option = dhcp_server_pb2.OptionData()
        if option_name is not None:
            option.name = option_name
        else:
            option.code = option_code
        await self.rpc.request("dhcp/server/v4/config/option/delete", option)

    async def list_client_classes(self):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        return "\n".join([str(d) for d in config.client_class])

    async def add_client_class(self, name: str, test: str, next_server=None):
        client_class = dhcp_server_pb2.ClientClass()
        client_class.name = name
        client_class.test = test
        if next_server is not None:
            client_class.next_server = next_server
        await self.rpc.request("dhcp/server/v4/config/client_class/add", client_class)

    async def update_client_class(
        self,
        client_class: str,
        test: str | None = None,
        next_server: IPv4Address | None = None,
    ):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        item = None
        for cc in config.client_class:
            if cc.name == client_class:
                item = cc
                break
        if not item:
            raise InvalidArgument("No such client-class: %s" % client_class)
        if test is not None:
            item.test = test
        if next_server is not None:
            item.next_server = str(next_server)
        await self.rpc.request("dhcp/server/v4/config/client_class/update", item)

    async def delete_client_class(self, client_class: str):
        item = dhcp_server_pb2.ClientClass()
        item.name = client_class
        await self.rpc.request("dhcp/server/v4/config/client_class/delete", item)

    async def list_client_class_option_definitions(self, client_class: str):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        item = None
        for cc in config.client_class:
            if cc.name == client_class:
                item = cc
                break
        if not item:
            raise InvalidArgument("No such client-class: %s" % client_class)

        return "\n".join([str(d) for d in item.option_definition])

    async def add_client_class_option_definition(
        self,
        client_class: str,
        name: str,
        code: UInt32,
        type: str,
        space: str | None = None,
        array: bool = None,
        record_types: str = None,
        encapsulate: str = None,
    ):
        item = dhcp_server_pb2.ClientClass()
        item.name = client_class
        option_definition = item.option_definition.add()
        option_definition.name = name
        option_definition.code = code
        option_definition.type = type
        if space is not None:
            option_definition.space = space
        if array is not None:
            option_definition.array = array
        if record_types is not None:
            option_definition.record_types = record_types
        if encapsulate is not None:
            option_definition.encapsulate = encapsulate
        await self.rpc.request(
            "dhcp/server/v4/config/client_class/option_definition/add", item
        )

    async def update_client_class_option_definition(
        self,
        client_class: str,
        client_class_option_definition: str,
        code: UInt32 = None,
        type=None,
        space=None,
        array: bool = None,
        record_types: str = None,
        encapsulate: str = None,
    ):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        item = None
        for cc in config.client_class:
            if cc.name == client_class:
                item = cc
                break
        if not item:
            raise InvalidArgument("No such client-class: %s" % client_class)

        option_definition = None
        for od in item.option_definition:
            if od.name == client_class_option_definition:
                option_definition = od
                break
        if not option_definition:
            raise InvalidArgument(
                "No such option-definition: %s" % client_class_option_definition
            )

        client_class_item = dhcp_server_pb2.ClientClass()
        client_class_item.name = client_class
        updated_option_definition = client_class_item.option_definition.add()
        updated_option_definition.CopyFrom(option_definition)
        if code is not None:
            updated_option_definition.code = code
        if type is not None:
            updated_option_definition.type = type
        if space is not None:
            updated_option_definition.space = space
        if array is not None:
            updated_option_definition.array = array
        if record_types is not None:
            updated_option_definition.record_types = record_types
        if encapsulate is not None:
            updated_option_definition.encapsulate = encapsulate
        await self.rpc.request(
            "dhcp/server/v4/config/client_class/option_definition/update",
            client_class_item,
        )

    async def delete_client_class_option_definition(
        self, client_class: str, client_class_option_definition: str
    ):
        item = dhcp_server_pb2.ClientClass()
        item.name = client_class
        option_definition = item.option_definition.add()
        option_definition.name = client_class_option_definition
        await self.rpc.request(
            "dhcp/server/v4/config/client_class/option_definition/delete", item
        )

    async def list_client_class_options(self, client_class: str):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        item = None
        for cc in config.client_class:
            if cc.name == client_class:
                item = cc
                break
        if not item:
            raise InvalidArgument("No such client-class: %s" % client_class)

        return "\n".join([str(d) for d in item.option])

    async def add_client_class_option(
        self,
        client_class: str,
        name: str = None,
        code: UInt32 = None,
        data: str = None,
    ):
        if name is None and code is None:
            raise InvalidArgument("name or code must be specified")
        if data is None:
            raise InvalidArgument("data must be specified")

        client_class_item = dhcp_server_pb2.ClientClass()
        client_class_item.name = client_class
        option = client_class_item.option.add()
        if name is not None:
            option.name = name
        if code is not None:
            option.code = code
        option.data = data
        await self.rpc.request(
            "dhcp/server/v4/config/client_class/option/add", client_class_item
        )

    async def update_client_class_option(
        self,
        client_class: str,
        client_class_option_name: str = None,
        client_class_option_code: UInt32 = None,
        data: str = None,
    ):
        field = None
        if client_class_option_name is not None:
            field = "name"
            field_value = client_class_option_name
        elif client_class_option_code is not None:
            field = "code"
            field_value = client_class_option_code

        if not field:
            raise InvalidArgument("name or code must be specified")

        if data is None:
            raise InvalidArgument("data must be specified")

        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        client_class_item = None
        for cc in config.client_class:
            if cc.name == client_class:
                client_class_item = cc
                break
        if not client_class_item:
            raise InvalidArgument("No such client-class: %s" % client_class)

        option = None
        for od in client_class_item.option:
            if getattr(od, field) == field_value:
                option = od
                break
        if not option:
            raise InvalidArgument("No such option with %s of %s" % (field, field_value))

        client_class_item = dhcp_server_pb2.ClientClass()
        client_class_item.name = client_class
        updated_option = client_class_item.option.add()
        updated_option.CopyFrom(option)
        updated_option.data = data
        await self.rpc.request(
            "dhcp/server/v4/config/client_class/option/update", client_class_item
        )

    async def delete_client_class_option(
        self,
        client_class: str,
        client_class_option_name: str = None,
        client_class_option_code: UInt32 = None,
    ):
        field = None
        if client_class_option_name is not None:
            field = "name"
            field_value = client_class_option_name
        elif client_class_option_code is not None:
            field = "code"
            field_value = client_class_option_code

        if not field:
            raise InvalidArgument("name or code must be specified")

        item = dhcp_server_pb2.ClientClass()
        item.name = client_class
        option = item.option.add()
        setattr(option, field, field_value)
        await self.rpc.request("dhcp/server/v4/config/client_class/option/delete", item)

    async def list_subnets(self):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        return "\n".join([str(d) for d in config.subnet])

    async def add_subnet(
        self,
        address: IPv4Network,
        use_ipam: bool = False,
        next_server: str = None,
    ):
        subnet = dhcp_server_pb2.DHCPv4Subnet()
        subnet.address = str(address)
        subnet.use_ipam = use_ipam
        if next_server is not None:
            subnet.next_server = next_server
        await self.rpc.request("dhcp/server/v4/config/subnet/add", subnet)

    async def update_subnet(
        self,
        subnet: IPv4Network,
        use_ipam: bool = False,
        next_server: str | None = None,
    ):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)
        address = str(subnet)
        subnet = None
        for sn in config.subnet:
            if sn.address == address:
                subnet = sn
                break
        if not subnet:
            raise InvalidArgument("No such subnet: %s" % address)

        if use_ipam is not None:
            subnet.use_ipam = use_ipam
        if next_server is not None:
            subnet.next_server = next_server

        await self.rpc.request("dhcp/server/v4/config/subnet/update", subnet)

    async def delete_subnet(self, subnet: IPv4Network):
        subnet = dhcp_server_pb2.DHCPv4Subnet()
        subnet.address = str(subnet)
        await self.rpc.request("dhcp/server/v4/config/subnet/delete", subnet)

    async def add_pool(
        self,
        subnet: IPv4Network,
        pool_definition: PoolDefinition,
    ):
        subnet_item = dhcp_server_pb2.DHCPv4Subnet()
        subnet_item.address = str(subnet)
        subnet_item.pool.append(str(pool_definition))
        await self.rpc.request("dhcp/server/v4/config/subnet/pool/add", subnet_item)

    async def delete_pool(
        self,
        subnet: IPv4Network,
        pool: PoolDefinition,
    ):
        subnet_item = dhcp_server_pb2.DHCPv4Subnet()
        subnet_item.address = str(subnet)
        subnet_item.pool.append(str(pool))
        await self.rpc.request("dhcp/server/v4/config/subnet/pool/delete", subnet_item)

    async def list_subnet_options(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        subnet_item = None
        for sn in config.subnet:
            if sn.address == str(subnet):
                subnet_item = sn
                break
        if not subnet_item:
            raise InvalidArgument("No such subnet: %s" % subnet)

        return "\n".join([str(d) for d in subnet_item.option])

    async def add_subnet_option(
        self,
        subnet: IPv4Network,
        name: str | None = None,
        code: UInt32 | None = None,
        data: str | None = None,
    ):
        if (name is None and code is None) or (name is not None and code is not None):
            raise InvalidArgument("one of name or code must be specified")
        if data is None:
            raise InvalidArgument("data must be specified")

        subnet_item = dhcp_server_pb2.DHCPv4Subnet()
        subnet_item.address = str(subnet)
        option = subnet_item.option.add()
        if name is not None:
            option.name = name
        if code is not None:
            option.code = code
        option.data = data
        await self.rpc.request("dhcp/server/v4/config/subnet/option/add", subnet_item)

    async def update_subnet_option(
        self,
        subnet: IPv4Network,
        subnet_option_name: str | None = None,
        subnet_option_code: UInt32 | None = None,
        data: str | None = None,
    ):
        field = None
        if subnet_option_name is not None:
            field = "name"
            field_value = subnet_option_name
        elif subnet_option_code is not None:
            field = "code"
            field_value = subnet_option_code

        if not field:
            raise InvalidArgument("name or code must be specified")

        if data is None:
            raise InvalidArgument("data must be specified")

        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        subnet_item = None
        for sn in config.subnet:
            if sn.address == str(subnet):
                subnet_item = sn
                break
        if not subnet_item:
            raise InvalidArgument("No such subnet: %s" % subnet)

        option = None
        for opt in subnet_item.option:
            if getattr(opt, field) == field_value:
                option = opt
                break
        if not option:
            raise InvalidArgument("No such option with %s of %s" % (field, field_value))

        updated_subnet = dhcp_server_pb2.DHCPv4Subnet()
        updated_subnet.address = str(subnet)
        updated_option = updated_subnet.option.add()
        updated_option.CopyFrom(option)
        updated_option.data = data
        await self.rpc.request(
            "dhcp/server/v4/config/subnet/option/update", updated_subnet
        )

    async def delete_subnet_option(
        self,
        subnet: IPv4Network,
        subnet_option_name: str | None = None,
        subnet_option_code: UInt32 | None = None,
    ):
        if (subnet_option_name is None and subnet_option_code is None) or (
            subnet_option_name is not None and subnet_option_code is not None
        ):
            raise InvalidArgument(
                "one of subnet_option_name or subnet_option_code must be specified"
            )

        subnet_item = dhcp_server_pb2.DHCPv4Subnet()
        subnet_item.address = str(subnet)
        option = subnet_item.option.add()
        if subnet_option_name is not None:
            option.name = subnet_option_name
        else:
            option.code = subnet_option_code
        await self.rpc.request(
            "dhcp/server/v4/config/subnet/option/delete", subnet_item
        )

    async def list_subnet_reservations(self, subnet: IPv4Network):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        subnet_item = None
        for sn in config.subnet:
            if sn.address == str(subnet):
                subnet_item = sn
                break
        if not subnet_item:
            raise InvalidArgument("No such subnet: %s" % subnet)

        return "\n".join([str(d) for d in subnet_item.reservation])

    async def add_subnet_reservation(
        self,
        subnet: IPv4Network,
        hardware_address: EUI,
        ip_address: IPv4Address,
    ):
        item = dhcp_server_pb2.DHCPv4Subnet()
        item.address = str(subnet)
        reservation = item.reservation.add()
        reservation.hardware_address = str(hardware_address)
        reservation.ip_address = str(ip_address)
        await self.rpc.request("dhcp/server/v4/config/subnet/reservation/add", item)

    async def update_subnet_reservation(
        self,
        subnet: IPv4Network,
        subnet_hardware_reservation: EUI,
        ip_address: IPv4Address,
    ):
        config = await self.rpc.request("dhcp/server/v4/config/get", None)

        subnet_item = None
        for sn in config.subnet:
            if sn.address == str(subnet):
                subnet_item = sn
                break
        if not subnet_item:
            raise InvalidArgument("No such subnet: %s" % subnet)

        reservation = None
        for res in subnet_item.reservation:
            if res.hardware_address == str(subnet_hardware_reservation):
                reservation = res
                break
        if not reservation:
            raise InvalidArgument(
                f"No such reservation: {subnet_hardware_reservation} in subnet {subnet}"
            )

        updated_subnet = dhcp_server_pb2.DHCPv4Subnet()
        updated_subnet.address = str(subnet)
        updated_reservation = updated_subnet.reservation.add()
        updated_reservation.CopyFrom(reservation)
        updated_reservation.hardware_address = str(subnet_hardware_reservation)
        updated_reservation.ip_address = str(ip_address)
        await self.rpc.request(
            "dhcp/server/v4/config/subnet/reservation/update", updated_subnet
        )

    async def delete_subnet_reservation(
        self,
        subnet: IPv4Network,
        subnet_hardware_reservation: EUI,
    ):
        sn = dhcp_server_pb2.DHCPv4Subnet()
        sn.address = str(subnet)
        reservation = sn.reservation.add()
        reservation.hardware_address = str(subnet_hardware_reservation)
        await self.rpc.request("dhcp/server/v4/config/subnet/reservation/delete", sn)

    async def add_relay_address(
        self,
        subnet: IPv4Network,
        ip_address: IPv4Address,
    ):
        sn = dhcp_server_pb2.DHCPv4Subnet()
        sn.address = str(subnet)
        sn.relay_address.append(str(ip_address))
        await self.rpc.request("dhcp/server/v4/config/subnet/relay_address/add", sn)

    async def delete_relay_address(
        self,
        subnet: IPv4Network,
        relay_address: IPv4Address,
    ):
        sn = dhcp_server_pb2.DHCPv4Subnet()
        sn.address = str(subnet)
        sn.relay_address.append(str(relay_address))
        await self.rpc.request("dhcp/server/v4/config/subnet/relay_address/delete", sn)

    async def show_subnet_leases(self, subnet: IPv4Network):
        item = dhcp_server_pb2.DHCPv4Subnet()
        item.address = str(subnet)
        return await self.rpc.request("dhcp/server/v4/subnet/leases", item)
