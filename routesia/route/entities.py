"""
routesia/route/route.py - Route support
"""

from routesia.entity import Entity
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
