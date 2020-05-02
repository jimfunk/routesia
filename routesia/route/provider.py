"""
routesia/route/provider.py - Route support
"""

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.server import Server
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.rtnetlink.events import (
    RouteAddEvent,
    RouteRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)
from routesia.route.entities import TableEntity


class RouteProvider(Provider):
    def __init__(
        self, server: Server, iproute: IPRouteProvider, config: ConfigProvider
    ):
        self.server = server
        self.iproute = iproute
        self.config = config
        self.tables = {
            253: TableEntity(self.iproute, 253, "default"),
            254: TableEntity(self.iproute, 254, "main"),
            255: TableEntity(self.iproute, 255, "local"),
        }

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
        self.configure()
