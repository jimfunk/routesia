"""
routesia/route/route.py - Route support
"""

from ipaddress import ip_network
import socket

from routesia.config import ConfigProvider
from routesia.entity import Entity
from routesia.injector import Provider
from routesia.server import Server
from routesia.rtnetlink.iproute import IPRouteProvider, RouteAddEvent, RouteRemoveEvent
from routesia.route.route_pb2 import RouteState


class TableEntity(Entity):
    def __init__(self, iproute, id, name=None, config=None):
        super().__init__(config=config)
        self.iproute = iproute
        self.id = id
        self.name = name
        if self.config and self.config.name:
            self.name = self.config.name
        self.routes = {}

    def update_config(self, config):
        self.config = config
        self.apply()

    def apply(self):
        pass


class RouteEntity(Entity):
    def __init__(self, iproute, table_id, destination, config=None, event=None):
        super().__init__(config=config)
        self.table_id = table_id
        self.destination = destination
        self.iproute = iproute
        self.ifindex = None
        self.carrier = False
        self.state = RouteState()
        if event:
            self.update_state(event, apply=False)
        print("New route %s in table %s. Config: %s" %
              (self.destination, self.table_id, self.config))
        self.apply()

    def update_state(self, event, apply=True):
        self.state.table_id = self.table_id
        self.state.destination = str(self.destination)
        self.state.protocol = event.message['proto']
        self.state.scope = event.message['scope']
        if 'RTA_PREFSRC' in event.attrs:
            self.state.preferred_source = event.attrs['RTA_PREFSRC']
        del self.state.nexthop[:]
        if 'RTA_GATEWAY' in event.attrs or 'RTA_OIF' in event.attrs:
            nexthop = self.state.nexthop.add()
            if 'RTA_GATEWAY' in event.attrs:
                nexthop.gateway = event.attrs['RTA_GATEWAY']
            if 'RTA_OIF' in event.attrs:
                nexthop.interface = self.iproute.interface_map[event.attrs['RTA_OIF']]
        elif 'RTA_MULTIPATH' in event.attrs:
            for message in event.attrs['RTA_MULTIPATH']:
                attrs = dict(message['attrs'])
                nexthop = self.state.nexthop.add()
                nexthop.interface = self.iproute.interface_map[message['oif']]
                if 'RTA_GATEWAY' in attrs:
                    nexthop.gateway = attrs['RTA_GATEWAY']

        if apply:
            self.apply()

    def handle_remove(self):
        self.state.Clear()
        self.apply()

    def update_config(self, config):
        self.config = config
        self.apply()

    def link(self, *args, **kwargs):
        if 'add' not in args:
            kwargs['index'] = self.ifindex
        return self.iproute.iproute.link(*args, **kwargs)

    def apply(self):
        if self.config is not None:
            if self.state.nexthop != self.config.nexthop:
                kwargs = {
                    'table': self.table_id,
                    'dst': str(self.destination),
                }
                if self.config.nexthop:
                    if len(self.config.nexthop) == 1:
                        nexthop = self.config.nexthop[0]
                        if nexthop.gateway:
                            kwargs['gateway'] = nexthop.gateway
                        if nexthop.interface:
                            if nexthop.interface not in self.iproute.interface_map:
                                print("Unknown interface %s in route %s. Not applying." % (
                                    nexthop.interface, self.destination))
                                return
                            kwargs['oif'] = self.iproute.interface_map[nexthop['interface']]
                    else:
                        multipath = []
                        for nexthop in self.config.nexthop:
                            nexthop_args = {}
                            if nexthop.gateway:
                                nexthop_args['gateway'] = nexthop.gateway
                            if nexthop.interface:
                                if nexthop.interface not in self.iproute.interface_map:
                                    print(
                                        "Unknown interface %s in multipath route. Skipping." % nexthop.interface)
                                    continue
                                nexthop_args['oif'] = self.iproute.interface_map[nexthop.interface]
                            multipath.append(nexthop_args)
                        if not multipath:
                            print(
                                "No valid multipath nexthops in route %s. Not applying." % self.destination)
                            return
                        kwargs['multipath'] = multipath

                self.iproute.iproute.route('replace', **kwargs)


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

        self.config.register_init_config_hook(self.init_config)
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
