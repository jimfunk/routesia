"""
routesia/route/route.py - Route support
"""

from ipaddress import ip_address, ip_network

from routesia.entity import Entity
from routesia.route.route_pb2 import RouteState


PROTO_ID = 52


class TableEntity(Entity):
    def __init__(self, iproute, id, name=None, config=None):
        super().__init__()
        self.config = config
        self.iproute = iproute
        self.id = id
        self.name = name
        if self.config and self.config.name:
            self.name = self.config.name
        self.routes = {}
        self.interfaces = set()

    def handle_config_change(self, config):
        self.config = config
        self.apply()

    def apply(self):
        configured_destinations = []

        for route_config in self.config.route:
            destination = ip_network(route_config.destination)
            configured_destinations.append(destination)
            if destination not in self.routes:
                self.routes[destination] = RouteEntity(self.iproute, self, destination)
            self.routes[destination].handle_config_change(route_config)

        for destination, route in self.routes.items():
            if destination not in configured_destinations and route.config:
                route.handle_config_remove()

    def find_route_config(self, event):
        if not self.config:
            return None
        for route_config in self.config.route:
            if ip_network(route_config.destination) == event.destination:
                return route_config
        return None

    def nexthop_accessible(self, nexthop):
        """
        Returns True if the nexthop is accessible
        """
        if not nexthop.gateway:
            # Interface route
            return nexthop.interface in self.interfaces

        gateway = ip_address(nexthop.gateway)

        for destination, route in self.routes.items():
            if gateway not in destination:
                continue
            for candidate in route.state.nexthop:
                if not candidate.interface:
                    continue
                if nexthop.interface and candidate.interface != nexthop.interface:
                    continue
                return True
        return False

    def dynamic_accessible(self, dynamic):
        """
        Returns True if the dynamic route is accessible
        """
        interface = dynamic["interface"]
        if interface:
            # Interface route
            return dynamic["interface"] in self.interfaces

        gateway = ip_address(dynamic["gateway"])

        for destination, route in self.routes.items():
            if gateway not in destination:
                continue
            for candidate in route.state.nexthop:
                if not candidate.interface:
                    continue
                if interface and candidate.interface != interface:
                    continue
                return True
        return False

    def add_dynamic_route(
        self, destination, gateway=None, interface=None, prefsrc=None, scope=None
    ):
        if destination in self.routes:
            # Don't overwrite an existing route
            return
        self.routes[destination] = RouteEntity(
            self.iproute,
            self,
            destination,
            dynamic={"gateway": gateway, "interface": interface, "prefsrc": prefsrc, "scope": scope},
        )

    def remove_dynamic_route(self, destination):
        if destination in self.routes:
            self.routes[destination].handle_dynamic_remove()

    def handle_route_add_event(self, event):
        if event.destination not in self.routes:
            self.routes[event.destination] = RouteEntity(
                self.iproute, self, event.destination
            )
        self.routes[event.destination].handle_add_event(event)

        # Check for dependent routes since they may be insertable now
        for route in self.routes.values():
            if route.config and not route.state.present:
                for nexthop in route.config.nexthop:
                    if (
                        nexthop.gateway
                        and ip_address(nexthop.gateway) in event.destination
                    ):
                        route.apply()

    def handle_route_remove_event(self, event):
        if event.destination in self.routes:
            route = self.routes[event.destination]
            route.handle_remove_event()
            if not route.config:
                del self.routes[event.destination]

    def handle_interface_add(self, event):
        self.interfaces.add(event.ifname)

        # Check for dependent routes since they may be insertable now
        for route in self.routes.values():
            if route.config and not route.state.present:
                for nexthop in route.config.nexthop:
                    if not nexthop.gateway and nexthop.interface == event.ifname:
                        try:
                            route.apply()
                        except Exception as e:
                            # TODO: This needs to filter on flags instead of attempting and ignoring
                            print(e)

    def handle_interface_remove(self, event):
        self.interfaces.remove(event.ifname)


class RouteEntity(Entity):
    def __init__(self, iproute, table: TableEntity, destination, dynamic=None):
        super().__init__()
        self.config = None
        self.table = table
        self.destination = destination
        self.dynamic = dynamic
        self.iproute = iproute
        self.ifindex = None
        self.carrier = False
        self.state = RouteState()
        self.route_args = None
        if dynamic:
            self.state.dynamic = True
            self.apply()

    def handle_add_event(self, event):
        self.state.present = True
        self.state.table_id = self.table.id
        self.state.destination = str(self.destination)
        self.state.protocol = event.message["proto"]
        self.state.scope = event.message["scope"]
        if "RTA_PREFSRC" in event.attrs:
            self.state.preferred_source = event.attrs["RTA_PREFSRC"]
        del self.state.nexthop[:]
        if "RTA_GATEWAY" in event.attrs or "RTA_OIF" in event.attrs:
            nexthop = self.state.nexthop.add()
            if "RTA_GATEWAY" in event.attrs:
                nexthop.gateway = event.attrs["RTA_GATEWAY"]
            if "RTA_OIF" in event.attrs:
                nexthop.interface = self.iproute.interface_map[event.attrs["RTA_OIF"]]
        elif "RTA_MULTIPATH" in event.attrs:
            for message in event.attrs["RTA_MULTIPATH"]:
                attrs = dict(message["attrs"])
                nexthop = self.state.nexthop.add()
                nexthop.interface = self.iproute.interface_map[message["oif"]]
                if "RTA_GATEWAY" in attrs:
                    nexthop.gateway = attrs["RTA_GATEWAY"]

        print("Route %s added in table %s" % (self.destination, self.table.id))
        self.apply()

    def handle_remove_event(self):
        print("Route %s removed from table %s" % (self.destination, self.table.id))
        self.state.Clear()
        if self.dynamic:
            self.state.dynamic = True
        self.apply()

    def handle_config_change(self, config):
        print("New route config in table %s:\n%s" % (self.table.id, config))
        self.config = config
        self.apply()

    def remove(self):
        if self.route_args:
            self.iproute.iproute.route("delete", **self.route_args)
            self.route_args = None

    def handle_config_remove(self, config):
        print(
            "Removed config for route %s in table %s"
            % (self.destination, self.table.id)
        )
        self.config = None
        self.remove()

    def handle_dynamic_remove(self):
        if self.dynamic:
            print(
                "Removed dynamic route %s in table %s"
                % (self.destination, self.table.id)
            )
            self.dynamic = None
            self.remove()

    def link(self, *args, **kwargs):
        if "add" not in args:
            kwargs["index"] = self.ifindex
        return self.iproute.iproute.link(*args, **kwargs)

    @property
    def insertable(self):
        """
        Returns whether the route can be inserted
        """
        if self.dynamic:
            return self.table.dynamic_accessible(self.dynamic)
        if self.config is None:
            return False
        for nexthop in self.config.nexthop:
            if not self.table.nexthop_accessible(nexthop):
                return False
        return True

    def apply(self):
        if not self.insertable:
            return

        if self.config:
            if self.state.nexthop != self.config.nexthop:
                kwargs = {
                    "table": self.table.id,
                    "dst": str(self.destination),
                    "proto": PROTO_ID,
                }
                if self.config.nexthop:
                    if len(self.config.nexthop) == 1:
                        nexthop = self.config.nexthop[0]
                        if nexthop.gateway:
                            kwargs["gateway"] = nexthop.gateway
                        if nexthop.interface:
                            if nexthop.interface not in self.iproute.interface_name_map:
                                print(
                                    "Unknown interface %s in route %s. Not applying."
                                    % (nexthop.interface, self.destination)
                                )
                                return
                            kwargs["oif"] = self.iproute.interface_name_map[
                                nexthop.interface
                            ]
                    else:
                        multipath = []
                        for nexthop in self.config.nexthop:
                            nexthop_args = {}
                            if nexthop.gateway:
                                nexthop_args["gateway"] = nexthop.gateway
                            if nexthop.interface:
                                if nexthop.interface not in self.iproute.interface_name_map:
                                    print(
                                        "Unknown interface %s in multipath route. Skipping."
                                        % nexthop.interface
                                    )
                                    continue
                                nexthop_args["oif"] = self.iproute.interface_name_map[
                                    nexthop.interface
                                ]
                            multipath.append(nexthop_args)
                        if not multipath:
                            print(
                                "No valid multipath nexthops in route %s. Not applying."
                                % self.destination
                            )
                            return
                        kwargs["multipath"] = multipath

                self.iproute.iproute.route("replace", **kwargs)
                self.route_args = kwargs
        elif self.dynamic:
            kwargs = {
                "table": self.table.id,
                "dst": str(self.destination),
                "proto": PROTO_ID,
            }
            if self.dynamic["interface"]:
                kwargs["oif"] = self.iproute.interface_name_map[
                    self.dynamic["interface"]
                ]
            if self.dynamic["gateway"]:
                kwargs["gateway"] = self.dynamic["gateway"]
            if self.dynamic["prefsrc"]:
                kwargs["prefsrc"] = self.dynamic["prefsrc"]
            if self.dynamic["scope"]:
                kwargs["scope"] = self.dynamic["scope"]
            self.iproute.iproute.route("replace", **kwargs)
            self.route_args = kwargs

    def to_message(self, message):
        "Set message parameters from entity state"
        message.CopyFrom(self.state)
