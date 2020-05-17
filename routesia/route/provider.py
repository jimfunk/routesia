"""
routesia/route/provider.py - Route support
"""

from ipaddress import ip_network

from routesia.config.provider import ConfigProvider
from routesia.exceptions import RPCInvalidParameters, RPCEntityExists, RPCEntityNotFound
from routesia.injector import Provider
from routesia.server import Server
from routesia.rpc.provider import RPCProvider
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.rtnetlink.events import (
    RouteAddEvent,
    RouteRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)
from routesia.route.entities import TableEntity
from routesia.route import route_pb2

DEFAULT_TABLES = {
    253: "default",
    254: "main",
    255: "local",
}


class RouteProvider(Provider):
    def __init__(
        self,
        server: Server,
        iproute: IPRouteProvider,
        config: ConfigProvider,
        rpc: RPCProvider,
    ):
        self.server = server
        self.iproute = iproute
        self.config = config
        self.rpc = rpc
        self.tables = {}
        for id, name in DEFAULT_TABLES.items():
            self.tables[id] = TableEntity(self.iproute, id, name)

        self.config.register_init_config_handler(self.init_config)
        self.config.register_change_handler(self.handle_config_change)
        self.server.subscribe_event(RouteAddEvent, self.handle_route_add)
        self.server.subscribe_event(RouteRemoveEvent, self.handle_route_remove)
        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

    def init_config(self, config):
        # Set the default tables. These are always present
        for table in self.tables.values():
            table_config = config.route.table.add()
            table_config.name = table.name
            table_config.id = table.id

    def handle_config_change(self, config):
        self.configure()

    def find_table_config(self, table_id):
        for table_config in self.config.data.route.table:
            if table_config.id == table_id:
                return table_config

    def configure(self):
        route_module_config = self.config.data.route
        for table_config in route_module_config.table:
            if table_config.id not in self.tables:
                self.tables[table_config.id] = TableEntity(
                    self.iproute, table_config.id, config=table_config
                )
            self.tables[table_config.id].handle_config_change(table_config)

    def handle_route_add(self, event):
        table_id = event.message["table"]
        if table_id not in self.tables:
            self.tables[table_id] = TableEntity(
                table_id, self.iproute, config=self.find_route_config(event)
            )
        self.tables[table_id].handle_route_add_event(event)

    def handle_route_remove(self, event):
        table_id = event.message["table"]
        if table_id not in self.tables:
            return
        self.tables[table_id].handle_route_remove_event(event)

    def handle_interface_add(self, event):
        for table in self.tables.values():
            table.handle_interface_add(event)

    def handle_interface_remove(self, event):
        for table in self.tables.values():
            table.handle_interface_remove(event)

    def startup(self):
        self.rpc.register("/route/list", self.rpc_list_routes)
        self.rpc.register("/route/table/list", self.rpc_list_tables)
        self.rpc.register("/route/config/get", self.rpc_get_config)
        self.rpc.register("/route/config/table/add", self.rpc_add_table)
        self.rpc.register("/route/config/table/update", self.rpc_update_table)
        self.rpc.register("/route/config/table/delete", self.rpc_delete_table)
        self.rpc.register("/route/config/route/get", self.rpc_get_route)
        self.rpc.register("/route/config/route/add", self.rpc_add_route)
        self.rpc.register("/route/config/route/update", self.rpc_update_route)
        self.rpc.register("/route/config/route/delete", self.rpc_delete_route)
        self.configure()

    def rpc_list_routes(self, msg: None) -> route_pb2.RouteStateList:
        routes = route_pb2.RouteStateList()
        for table in self.tables.values():
            for route in table.routes.values():
                route_msg = routes.route.add()
                route.to_message(route_msg)
        return routes

    def rpc_list_tables(self, msg: None) -> route_pb2.RouteTableConfigList:
        tables = route_pb2.RouteTableConfigList()
        for table in self.tables.values():
            table_msg = tables.table.add()
            table_msg.id = table.id
            table_msg.name = table.name
        return tables

    def rpc_get_config(self, msg: None) -> route_pb2.RouteTableConfigList:
        return self.config.staged_data.route

    def rpc_add_table(self, msg: route_pb2.RouteTableConfig) -> None:
        if not msg.id:
            raise RPCInvalidParameters("id not specified")
        for table in self.config.staged_data.route.table:
            if table.id == msg.id:
                raise RPCEntityExists("id %s" % msg.id)
            if msg.name and table.name == msg.name:
                raise RPCEntityExists("name %s" % msg.name)

        table = self.config.staged_data.route.table.add()
        table.CopyFrom(msg)

    def rpc_update_table(self, msg: route_pb2.RouteTableConfig) -> None:
        if not msg.id:
            raise RPCInvalidParameters("id not specified")
        for table in self.config.staged_data.route.table:
            if table.id == msg.id:
                table.name = msg.name
                return

    def rpc_delete_table(self, msg: route_pb2.RouteTableConfig) -> None:
        if not msg.id:
            raise RPCInvalidParameters("id not specified")
        if msg.id in DEFAULT_TABLES:
            raise RPCInvalidParameters("Cannot remove default table")
        for i, table in enumerate(self.config.staged_data.route.table):
            if table.id == msg.id:
                del self.config.staged_data.route.table[i]
                return

    def get_table(self, id, name):
        """
        Get the table with the given id or name. If neither are givem returns
        table 254 (main)
        """
        if name:
            for table in self.config.staged_data.route.table:
                if table.name == name:
                    return table
            raise RPCEntityNotFound(name)

        if not id:
            id = 254

        for table in self.config.staged_data.route.table:
            if table.id == id:
                return table
        raise RPCEntityNotFound(str(id))

    def rpc_get_route(self, msg: route_pb2.RouteTableConfig) -> route_pb2.RouteTableConfig:
        table = self.get_table(msg.id, msg.name)

        destination = ip_network(msg.route[0].destination)

        for route in table.route:
            if ip_network(route.destination) == destination:
                route_table = route_pb2.RouteTableConfig()
                route_table.id = table.id
                route_table.name = table.name
                route_route = route_table.route.add()
                route_route.CopyFrom(route)
                return route_table
        raise RPCEntityNotFound(str(destination))

    def rpc_add_route(self, msg: route_pb2.RouteTableConfig) -> None:
        table = self.get_table(msg.id, msg.name)

        destination = ip_network(msg.route[0].destination)

        for route in table.route:
            if ip_network(route.destination) == destination:
                raise RPCEntityExists(str(destination))

        route = table.route.add()
        route.CopyFrom(msg.route[0])

    def rpc_update_route(self, msg: route_pb2.RouteTableConfig) -> None:
        table = self.get_table(msg.id, msg.name)

        destination = ip_network(msg.route[0].destination)

        for route in table.route:
            if ip_network(route.destination) == destination:
                route.CopyFrom(msg.route[0])
                return

    def rpc_delete_route(self, msg: route_pb2.RouteTableConfig) -> None:
        table = self.get_table(msg.id, msg.name)

        destination = ip_network(msg.route[0].destination)

        for i, route in enumerate(table.route):
            if ip_network(route.destination) == destination:
                del table.route[i]
                return
