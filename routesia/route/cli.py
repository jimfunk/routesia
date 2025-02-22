"""
routesia/route/route/commands.py - Routesia route commands
"""

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from routesia.cli.completion import Completion
from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import UInt16, UInt32
from routesia.rpcclient import RPCClient
from routesia.schema.v1 import route_pb2
from routesia.service import Provider


DEFAULT_TABLE = 254


class RouteCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("route")
        self.rpc = rpc

        self.cli.add_argument_completer("system-table", self.complete_system_table)
        self.cli.add_argument_completer("table", self.complete_config_table)
        self.cli.add_argument_completer("interface", self.complete_interface)
        self.cli.add_argument_completer("destination", self.complete_destination)
        self.cli.add_argument_completer("nexthop-gateway", self.complete_nexthop_gateway)
        self.cli.add_argument_completer("nexthop-interface", self.complete_nexthop_interface)

        self.cli.add_command("route show @table!system-table", self.show_route)
        self.cli.add_command("route table show", self.show_table)
        self.cli.add_command("route config table add :table! :name", self.add_table)
        self.cli.add_command("route config table update :table @name", self.update_table)
        self.cli.add_command("route config table delete :table", self.delete_table)
        self.cli.add_command("route config route add :destination @table @gateway @interface @hops", self.add_route)
        self.cli.add_command("route config route delete @destination @table", self.delete_route)
        self.cli.add_command("route config route nexthop add @destination @table @gateway @interface @hops", self.add_nexthop)
        self.cli.add_command("route config route nexthop delete @destination @table @gateway @interface", self.delete_nexthop)

    async def complete_system_table(self):
        completions = []
        tables = await self.rpc.request("route/table/list")
        for table in tables.table:
            if table.name:
                completions.append(
                    Completion(str(table.id), display=f"{table.id} {table.name}")
                )
            else:
                completions.append(str(table.id))
        return completions

    async def show_route(self, table: UInt32 = 0):
        routes = await self.rpc.request("route/list")
        if table:
            table_routes = route_pb2.RouteStateList()
            for route_state in routes.route:
                if route_state.table_id == table:
                    table_route = table_routes.route.add()
                    table_route.CopyFrom(route_state)
            return table_routes
        return routes

    async def show_table(self):
        return await self.rpc.request("route/table/list")

    async def add_table(self, table: UInt32, name: str | None = None):
        table_config = route_pb2.RouteTableConfig()
        table_config.id = table
        if name is not None:
            table_config.name = name
        await self.rpc.request("route/config/table/add", table_config)

    async def complete_config_table(self, destination: IPv4Network | IPv6Network | None = None):
        completions = []
        tables = await self.rpc.request("route/config/get")
        for table in tables.table:
            if destination is not None:
                destination = str(destination)
                for route in table.route:
                    if route.destination == destination:
                        if table.name:
                            completions.append(Completion(str(table.id), display=f"{table.id} {table.name}"))
                        else:
                            completions.append(str(table.id))
                        break
            else:
                completions.append(
                    Completion(str(table.id), display=f"{table.id} {table.name}")
                )
        return completions

    async def update_table(self, table: UInt32, name: str | None = None):
        table_config = route_pb2.RouteTableConfig()
        table_config.id = table
        if name is not None:
            table_config.name = name
        await self.rpc.request("route/config/table/update", table_config)

    async def delete_table(self, table: UInt32):
        table_config = route_pb2.RouteTableConfig()
        table_config.id = table
        await self.rpc.request("route/config/table/delete", table_config)

    async def complete_interface(self):
        completions = []
        interfaces = await self.rpc.request("interface/config/list")
        for interface in interfaces.interface:
            completions.append(interface.name)
        return completions

    async def add_route(
        self,
        destination: IPv4Network | IPv6Network,
        table: UInt32 | None = DEFAULT_TABLE,
        gateway: IPv4Address | IPv6Address | None = None,
        interface: str | None = None,
        hops: UInt32 | None = None,
    ):
        table_config = route_pb2.RouteTableConfig()
        table_config.id = table
        route = table_config.route.add()
        route.destination = str(destination)
        nexthop = route.nexthop.add()
        if gateway is not None:
            nexthop.gateway = str(gateway)
        if interface is not None:
            nexthop.interface = interface
        if hops is not None:
            nexthop.hops = hops
        await self.rpc.request("route/config/route/add", table_config)

    async def complete_destination(self, table: UInt32 = DEFAULT_TABLE):
        completions = []
        tables = await self.rpc.request("route/config/get")
        for table_config in tables.table:
            if table_config.id == table:
                for route in table_config.route:
                    completions.append(route.destination)
        return completions

    async def delete_route(self, destination: IPv4Network | IPv6Network, table: UInt32 = DEFAULT_TABLE):
        table_obj = route_pb2.RouteTableConfig()
        table_obj.id = table
        route = table_obj.route.add()
        route.destination = str(destination)
        await self.rpc.request("route/config/route/delete", table_obj)

    async def add_nexthop(
        self,
        destination: IPv4Network | IPv6Network,
        table: UInt32 | None = DEFAULT_TABLE,
        gateway: IPv4Address | IPv6Address | None = None,
        interface: str | None = None,
        hops: UInt32 | None = None,
    ):
        table_config = route_pb2.RouteTableConfig()
        table_config.id = table
        route = table_config.route.add()
        route.destination = str(destination)
        table_config = await self.rpc.request("route/config/route/get", table_config)
        if not table_config.route:
            raise InvalidArgument("Route not found")
        route = table_config.route[0]

        nexthop = route.nexthop.add()
        if gateway is not None:
            nexthop.gateway = str(gateway)
        if interface is not None:
            nexthop.interface = interface
        if hops is not None:
            nexthop.hops = hops
        await self.rpc.request("route/config/route/update", table_config)

    async def complete_nexthop_gateway(
        self,
        destination: IPv4Network | IPv6Network | None = None,
        table: UInt32 = DEFAULT_TABLE,
        interface: str | None = None,
    ):
        completions = []
        if destination is not None:
            destination = str(destination)
            tables = await self.rpc.request("route/config/get")
            for table_config in tables.table:
                if table_config.id != table:
                    continue
                for route in table_config.route:
                    if route.destination == destination:
                        for nexthop in route.nexthop:
                            if interface is not None and nexthop.interface != interface:
                                continue
                            if nexthop.gateway:
                                completions.append(nexthop.gateway)
                        return completions
        return completions

    async def complete_nexthop_interface(
        self,
        destination: IPv4Network | IPv6Network | None = None,
        table: UInt32 = DEFAULT_TABLE,
        gateway: IPv4Address | IPv6Address | None = None,
    ):
        completions = []
        if destination is not None:
            destination = str(destination)
            if gateway is not None:
                gateway = str(gateway)
            tables = await self.rpc.request("route/config/get")
            for table_config in tables.table:
                if table_config.id != table:
                    continue
                for route in table_config.route:
                    if route.destination == destination:
                        for nexthop in route.nexthop:
                            if gateway is not None and nexthop.gateway != gateway:
                                continue
                            if nexthop.interface:
                                completions.append(nexthop.interface)
                        return completions
        return completions

    async def delete_nexthop(
        self,
        destination: IPv4Network | IPv6Network,
        table: UInt32 = DEFAULT_TABLE,
        gateway: IPv4Address | IPv6Address | None = None,
        interface: str | None = None,
    ):
        table_config = route_pb2.RouteTableConfig()
        table_config.id = table
        route = table_config.route.add()
        route.destination = str(destination)
        table_config = await self.rpc.request("route/config/route/get", table_config)
        if not table_config.route:
            raise InvalidArgument("Route not found")
        route = table_config.route[0]

        if gateway is not None:
            gateway = str(gateway)

        for i, nexthop in enumerate(route.nexthop):
            if gateway is not None and (not nexthop.gateway or nexthop.gateway != gateway):
                continue
            if interface is not None and nexthop.interface != interface:
                continue
            del route.nexthop[i]
            break

        await self.rpc.request("route/config/route/update", table_config)
