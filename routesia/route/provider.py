"""
routesia/route/provider.py - Route support
"""

from ipaddress import ip_network
import socket

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.server import Server
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.rtnetlink.events import RouteAddEvent, RouteRemoveEvent
from routesia.route.entities import RouteEntity, TableEntity


class RouteProvider(Provider):
    def __init__(self, server: Server, iproute: IPRouteProvider, config: ConfigProvider):
        self.server = server
        self.iproute = iproute
        self.config = config
        self.tables = {
            253: TableEntity(self.iproute, 253, 'default'),
            254: TableEntity(self.iproute, 254, 'main'),
            255: TableEntity(self.iproute, 255, 'local'),
        }

        self.config.register_init_config_handler(self.init_config)
        self.server.subscribe_event(RouteAddEvent, self.handle_route_add)
        self.server.subscribe_event(RouteRemoveEvent, self.handle_route_remove)

    def init_config(self, data):
        # Set the default tables. These are always present
        for table in self.tables.values():
            table_config = data.route.table.add()
            table_config.name = table.name
            table_config.id = table.id

    def handle_config_update(self, old, new):
        pass

    def find_table_config(self, table_id):
        for table_config in self.config.data.route.table:
            if table_config.id == table_id:
                return table_config

    def find_route_config(self, event):
        for table_config in self.config.data.route.table:
            if table_config.id == event.message['table']:
                for static_route_config in table_config.static:
                    if ip_network(static_route_config.destination) == event.destination:
                        return static_route_config

    def handle_route_add(self, event):
        table_id = event.message['table']
        if table_id not in self.tables:
            self.tables[table_id] = TableEntity(
                table_id, self.iproute, config=self.find_route_config(event))

        table = self.tables[table_id]

        if event.destination in table.routes:
            table.routes[event.destination].update_state(event)
        else:
            table.routes[event.destination] = RouteEntity(
                self.iproute, table_id, event.destination, config=self.find_route_config(event), event=event)

    def handle_route_remove(self, event):
        table_id = event.message['table']
        if table_id not in self.tables:
            return

        table = self.tables[table_id]
        if 'RTA_DST' in event.attrs:
            dst = ip_network('%s/%s' %
                             (event.attrs['RTA_DST'], event.message['dst_len']))
        else:
            if event.message['family'] == socket.AF_INET:
                dst = ip_network(
                    '0.0.0.0/%s' % event.message['dst_len'])
            else:
                dst = ip_network('::/%s' % event.message['dst_len'])

        if dst in table.routes:
            route = table.routes[dst]
            route.handle_remove()
            if not route.config:
                del table.routes[dst]

    def startup(self):
        route_module_config = self.config.data.route
        for table_config in route_module_config.table:
            if table_config.id not in self.tables:
                self.tables[table_config.id] = TableEntity(
                    self.iproute, table_config.id, config=table_config)
            table = self.tables[table_config.id]
            for static_route_config in table_config.static:
                if static_route_config.destination not in table.routes:
                    table.routes[static_route_config.destination] = RouteEntity(
                        self.iproute, table.id, static_route_config.destination, config=static_route_config)
