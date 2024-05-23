"""
routesia/route/route.py - Route support
"""

from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
    ip_network,
)
import logging

from routesia.dhcp.client.events import DHCPv4LeasePreinit
from routesia.schema.v1.route_pb2 import RouteState


logger = logging.getLogger(__name__)


PROTO_ID = 52

RT_SCOPE_UNIVERSE = 0
RT_SCOPE_SITE = 200
RT_SCOPE_LINK = 253
RT_SCOPE_HOST = 254
RT_SCOPE_NOWHERE = 255


class TableEntity:
    def __init__(self, iproute, id, name=None, config=None):
        super().__init__()
        self.config = config
        self.iproute = iproute
        self.id = id
        self.name = name
        if self.config and self.config.name:
            self.name = self.config.name
        self.routes = {}
        self.dhcp_routes: dict[
            str, dict[IPv4Address | IPv6Address, DHCPRouteEntity]
        ] = {}
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

    def gateway_accessible(self, gateway: IPv4Address | IPv6Address):
        """
        Returns True if the gateway is accessible
        """
        for destination, route in self.routes.items():
            if gateway not in destination:
                continue
            for candidate in route.state.nexthop:
                if not candidate.interface:
                    continue
                return True
        return False

    def handle_dhcp_lease_preinit(self, event: DHCPv4LeasePreinit):
        if event.address and event.interface in self.dhcp_routes:
            if event.address.network in self.dhcp_routes[event.interface]:
                route = self.dhcp_routes[event.interface][event.address.network]
                route.remove()
                del self.dhcp_routes[event.interface][event.address.network]
                if not self.dhcp_routes[event.interface]:
                    del self.dhcp_routes[event.interface]

    def handle_dhcp_lease_acquired(self, event: DHCPv4LeasePreinit):
        existing = set()
        new = set()
        if event.interface in self.dhcp_routes:
            for route in self.dhcp_routes[event.interface].values():
                existing.add((route.destination, route.gateway))
        else:
            self.dhcp_routes[event.interface] = {}
        new.add((event.address.network, None))
        if event.gateway:
            new.add((ip_network("0.0.0.0/0"), event.gateway))
        for route in event.routes:
            new.add((route.destination, route.gateway))

        for destination, _ in existing - new:
            route = self.dhcp_routes[event.interface].pop(destination)
            route.remove()

        for destination, gateway in new - existing:
            logger.info(f"Adding DHCP route {destination} via {gateway or event.interface}")
            self.dhcp_routes[event.interface][destination] = DHCPRouteEntity(
                self.iproute,
                self,
                event.interface,
                destination,
                gateway,
                event.address.ip,
            )
            self.dhcp_routes[event.interface][destination].apply()

    def handle_dhcp_lease_lost(self, event: DHCPv4LeasePreinit):
        if event.interface in self.dhcp_routes:
            for route in self.dhcp_routes[event.interface].values():
                route.remove()
            del self.dhcp_routes[event.interface]

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
                        route.apply()

    def handle_interface_remove(self, event):
        self.interfaces.remove(event.ifname)


class RouteEntity:
    def __init__(self, iproute, table: TableEntity, destination):
        super().__init__()
        self.config = None
        self.table = table
        self.destination = destination
        self.iproute = iproute
        self.ifindex = None
        self.carrier = False
        self.state = RouteState()
        self.route_args = None

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
                nexthop.interface = self.iproute.get_interface_name_by_index(
                    event.attrs["RTA_OIF"]
                )
        elif "RTA_MULTIPATH" in event.attrs:
            for message in event.attrs["RTA_MULTIPATH"]:
                attrs = dict(message["attrs"])
                nexthop = self.state.nexthop.add()
                nexthop.interface = self.iproute.get_interface_name_by_index(
                    message["oif"]
                )
                if "RTA_GATEWAY" in attrs:
                    nexthop.gateway = attrs["RTA_GATEWAY"]

        logger.debug("Route %s added in table %s" % (self.destination, self.table.id))

    def handle_remove_event(self):
        logger.debug(
            "Route %s removed from table %s" % (self.destination, self.table.id)
        )
        self.state.Clear()
        self.apply()

    def handle_config_change(self, config):
        logger.debug("New route config in table %s:\n%s" % (self.table.id, config))
        self.config = config
        self.apply()

    def remove(self):
        if self.route_args:
            self.iproute.iproute.route("delete", **self.route_args)
            self.route_args = None

    def handle_config_remove(self):
        logger.debug(
            "Removed config for route %s in table %s"
            % (self.destination, self.table.id)
        )
        self.config = None
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
                                logger.warning(
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
                                if (
                                    nexthop.interface
                                    not in self.iproute.interface_name_map
                                ):
                                    logger.warning(
                                        "Unknown interface %s in multipath route. Skipping."
                                        % nexthop.interface
                                    )
                                    continue
                                nexthop_args["oif"] = self.iproute.interface_name_map[
                                    nexthop.interface
                                ]
                            multipath.append(nexthop_args)
                        if not multipath:
                            logger.warning(
                                "No valid multipath nexthops in route %s. Not applying."
                                % self.destination
                            )
                            return
                        kwargs["multipath"] = multipath

                self.iproute.iproute.route("replace", **kwargs)
                self.route_args = kwargs

    def to_message(self, message):
        "Set message parameters from entity state"
        message.CopyFrom(self.state)


class DHCPRouteEntity(RouteEntity):
    def __init__(
        self,
        iproute,
        table: TableEntity,
        interface: str,
        destination: IPv4Network | IPv6Network,
        gateway: IPv4Address | IPv6Address,
        prefsrc: IPv4Address | IPv6Address,
    ):
        self.interface = interface
        self.gateway = gateway
        self.prefsrc = prefsrc
        super().__init__(iproute, table, destination)

    @property
    def insertable(self):
        """
        Returns whether the route can be inserted
        """
        if self.gateway:
            return self.table.gateway_accessible(self.gateway)
        return True

    def apply(self):
        if not self.insertable:
            return

        kwargs = {
            "table": self.table.id,
            "dst": str(self.destination),
            "proto": PROTO_ID,
        }
        kwargs["oif"] = self.iproute.interface_name_map[self.interface]
        if self.gateway:
            kwargs["gateway"] = str(self.gateway)
        kwargs["prefsrc"] = str(self.prefsrc)

        if not self.gateway:
            kwargs["scope"] = RT_SCOPE_LINK

        self.iproute.iproute.route("replace", **kwargs)
        self.route_args = kwargs

    def to_message(self, message):
        "Set message parameters from entity state"
        self.state.dynamic = True
        super().to_message(message)
