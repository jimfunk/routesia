"""
routesia/route/route/commands.py - Routesia route commands
"""
from ipaddress import ip_address
from prompt_toolkit.completion import Completion

from routesia.cli import CLI, InvalidArgument
from routesia.rpcclient import RPCClient
from routesia.service import Provider


DEFAULT_TABLE = 254


async def get_table_completions(client, suggestion, **kwargs):
    completions = []
    tables = route_pb2.RouteTableConfigList.FromString(
        await client.request("/route/table/list", None)
    )
    for table in tables.table:
        completions.append(
            Completion(str(table.id), display="%s %s" % (table.id, table.name))
        )
    return completions


class RouteShow(CLICommand):
    command = "route show"
    parameters = (("table", UInt32(completer=get_table_completions)),)

    async def call(self, table=0):
        data = await self.client.request("/route/list", None)
        routes = route_pb2.RouteStateList.FromString(data)
        if table:
            table_routes = route_pb2.RouteStateList()
            for route_state in routes.route:
                if route_state.table_id == table:
                    table_route = table_routes.route.add()
                    table_route.CopyFrom(route_state)
            return table_routes
        return routes


class RouteTableShow(CLICommand):
    command = "route table show"

    async def call(self, table=0):
        return route_pb2.RouteTableConfigList.FromString(
            await self.client.request("/route/table/list", None)
        )


class RouteConfigTableAdd(CLICommand):
    command = "route config table add"
    parameters = (
        ("id", UInt32(required=True)),
        ("name", String()),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        self.update_message_from_args(table, **kwargs)
        await self.client.request("/route/config/table/add", table)


async def get_config_table_completions(client, suggestion, **kwargs):
    completions = []
    tables = route_pb2.RouteTableConfigList.FromString(
        await client.request("/route/config/get", None)
    )
    for table in tables.table:
        if "destination" in kwargs:
            for route in table.route:
                if route.destination == kwargs["destination"]:
                    completions.append(table.name)
                    break
        else:
            completions.append(
                Completion(str(table.id), display="%s %s" % (table.id, table.name))
            )
    return completions


async def get_config_table_name_completions(client, suggestion, **kwargs):
    completions = []
    tables = route_pb2.RouteTableConfigList.FromString(
        await client.request("/route/config/get", None)
    )
    for table in tables.table:
        if "destination" in kwargs:
            for route in table.route:
                if route.destination == kwargs["destination"]:
                    completions.append(table.name)
                    break
        else:
            completions.append(table.name)
    return completions


class RouteConfigTableUpdate(CLICommand):
    command = "route config table update"
    parameters = (
        ("id", UInt32(required=True, completer=get_config_table_completions)),
        ("name", String()),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        self.update_message_from_args(table, **kwargs)
        await self.client.request("/route/config/table/update", table)


class RouteConfigTableDelete(CLICommand):
    command = "route config table delete"
    parameters = (
        ("id", UInt32(required=True, completer=get_config_table_completions)),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        self.update_message_from_args(table, **kwargs)
        await self.client.request("/route/config/table/delete", table)


class RouteConfigRouteAdd(CLICommand):
    command = "route config route add"
    parameters = (
        ("destination", IPNetwork(required=True)),
        ("gateway", IPAddress()),
        ("interface", ConfiguredInterfaceParameter()),
        ("hops", UInt32()),
        ("table_id", UInt32(completer=get_config_table_completions)),
        ("table_name", String(completer=get_config_table_name_completions)),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        if "table_id" in kwargs:
            table.id = kwargs["table_id"]
        elif "table_name" in kwargs:
            table.name = kwargs["table_name"]
        route = table.route.add()
        route.destination = kwargs["destination"]
        nexthop = route.nexthop.add()
        for param in ("gateway", "interface", "hops"):
            if param in kwargs:
                setattr(nexthop, param, kwargs[param])
        await self.client.request("/route/config/route/add", table)


async def get_config_destination_completions(client, suggestion, **kwargs):
    completions = []
    tables = route_pb2.RouteTableConfigList.FromString(
        await client.request("/route/config/get", None)
    )
    for table in tables.table:
        if ("table_id" in kwargs and table.id != kwargs["table_id"]) or (
            "table_name" in kwargs and table.name != kwargs["table_name"]
        ):
            continue
        elif table.id != DEFAULT_TABLE:
            continue
        for route in table.route:
            completions.append(route.destination)
    return completions


class RouteConfigRouteNexthopAdd(CLICommand):
    command = "route config route nexthop add"
    parameters = (
        (
            "destination",
            IPNetwork(required=True, completer=get_config_destination_completions),
        ),
        ("gateway", IPAddress()),
        ("interface", ConfiguredInterfaceParameter()),
        ("hops", UInt32()),
        ("table_id", UInt32(completer=get_config_table_completions)),
        ("table_name", String(completer=get_config_table_name_completions)),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        if "table_id" in kwargs:
            table.id = kwargs["table_id"]
        elif "table_name" in kwargs:
            table.name = kwargs["table_name"]
        route = table.route.add()
        route.destination = kwargs["destination"]
        table = route_pb2.RouteTableConfig.FromString(
            await self.client.request("/route/config/route/get", table)
        )
        route = table.route[0]

        nexthop = route.nexthop.add()
        for param in ("gateway", "interface", "hops"):
            if param in kwargs:
                setattr(nexthop, param, kwargs[param])

        await self.client.request("/route/config/route/update", table)


async def get_config_nexthop_gateway_completions(client, suggestion, **kwargs):
    completions = []
    if "destination" in kwargs:
        tables = route_pb2.RouteTableConfigList.FromString(
            await client.request("/route/config/get", None)
        )
        for table in tables.table:
            if ("table_id" in kwargs and table.id != kwargs["table_id"]) or (
                "table_name" in kwargs and table.name != kwargs["table_name"]
            ):
                continue
            elif table.id != DEFAULT_TABLE:
                continue
            for route in table.route:
                if route.destination == kwargs["destination"]:
                    for nexthop in route.nexthop:
                        if (
                            "interface" in kwargs
                            and nexthop.interface != kwargs["interface"]
                        ):
                            continue
                        if nexthop.gateway:
                            completions.append(nexthop.gateway)
                    return completions
    return completions


async def get_config_nexthop_interface_completions(client, suggestion, **kwargs):
    completions = []
    if "destination" in kwargs:
        tables = route_pb2.RouteTableConfigList.FromString(
            await client.request("/route/config/get", None)
        )
        for table in tables.table:
            if ("table_id" in kwargs and table.id != kwargs["table_id"]) or (
                "table_name" in kwargs and table.name != kwargs["table_name"]
            ):
                continue
            elif table.id != DEFAULT_TABLE:
                continue
            for route in table.route:
                if route.destination == kwargs["destination"]:
                    for nexthop in route.nexthop:
                        if "gateway" in kwargs and nexthop.gateway != kwargs["gateway"]:
                            continue
                        if nexthop.interface:
                            completions.append(nexthop.interface)
                    return completions
    return completions


class RouteConfigRouteNexthopDelete(CLICommand):
    command = "route config route nexthop delete"
    parameters = (
        (
            "destination",
            IPNetwork(required=True, completer=get_config_destination_completions),
        ),
        ("gateway", IPAddress(completer=get_config_nexthop_gateway_completions)),
        (
            "interface",
            String(max_length=15, completer=get_config_nexthop_interface_completions),
        ),
        ("table_id", UInt32(completer=get_config_table_completions)),
        ("table_name", String(completer=get_config_table_name_completions)),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        if "table_id" in kwargs:
            table.id = kwargs["table_id"]
        elif "table_name" in kwargs:
            table.name = kwargs["table_name"]
        route = table.route.add()
        route.destination = kwargs["destination"]
        table = route_pb2.RouteTableConfig.FromString(
            await self.client.request("/route/config/route/get", table)
        )
        route = table.route[0]

        for i, nexthop in enumerate(route.nexthop):
            if "gateway" in kwargs and (
                not nexthop.gateway
                or ip_address(nexthop.gateway) != ip_address(kwargs["gateway"])
            ):
                continue
            if "interface" in kwargs and nexthop.interface != kwargs["interface"]:
                continue
            del route.nexthop[i]
            break

        await self.client.request("/route/config/route/update", table)


class RouteConfigRouteDelete(CLICommand):
    command = "route config route delete"
    parameters = (
        (
            "destination",
            IPNetwork(required=True, completer=get_config_destination_completions),
        ),
        ("table_id", UInt32(completer=get_config_table_completions)),
        ("table_name", String(completer=get_config_table_name_completions)),
    )

    async def call(self, **kwargs):
        table = route_pb2.RouteTableConfig()
        if "table_id" in kwargs:
            table.id = kwargs["table_id"]
        elif "table_name" in kwargs:
            table.name = kwargs["table_name"]
        route = table.route.add()
        route.destination = kwargs["destination"]
        await self.client.request("/route/config/route/delete", table)


class RouteCommandSet(CLICommandSet):
    commands = (
        RouteShow,
        RouteTableShow,
        RouteConfigTableAdd,
        RouteConfigTableUpdate,
        RouteConfigTableDelete,
        RouteConfigRouteAdd,
        RouteConfigRouteNexthopAdd,
        RouteConfigRouteNexthopDelete,
        RouteConfigRouteDelete,
    )
