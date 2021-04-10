"""
routesia/dhcp/client/entities.py - DHCP client entities
"""

from ipaddress import ip_address, ip_interface, ip_network
import logging

from routesia.dhcp.client.dhcpclient_pb2 import DHCPClientEventType, DHCPv4ClientStatus
from routesia.entity import Entity


logger = logging.getLogger(__name__)


class DHCPv4Client(Entity):
    def __init__(
        self, systemd, config, address_provider, interface_provider, route_provider
    ):
        self.systemd = systemd
        self.config = config
        self.address_provider = address_provider
        self.interface_provider = interface_provider
        self.route_provider = route_provider
        self.interface = config.interface
        self.status = DHCPv4ClientStatus()
        self.status.interface = self.interface

    @property
    def unit(self):
        return "routesia-dhcpv4-client@%s.service" % self.interface

    def on_config_change(self, config):
        old_config = self.config
        self.config = config
        if old_config is None:
            self.start()
        elif old_config.SerializeToString() != self.config.SerializeToString():
            if old_config.interface != self.config.interface:
                self.stop()
                self.interface = self.config.interface
                self.start()
            else:
                self.start()

    def on_event(self, event):
        self.status.last_event.CopyFrom(event)
        if event.type == DHCPClientEventType.Value("PREINIT"):
            self.on_preinit(event)
        elif event.type in (
            DHCPClientEventType.Value("BOUND"),
            DHCPClientEventType.Value("RENEW"),
            DHCPClientEventType.Value("REBIND"),
            DHCPClientEventType.Value("REBOOT"),
        ):
            self.on_update(event)
        elif event.type in (
            DHCPClientEventType.Value("EXPIRE"),
            DHCPClientEventType.Value("FAIL"),
            DHCPClientEventType.Value("RELEASE"),
            DHCPClientEventType.Value("STOP"),
            DHCPClientEventType.Value("TIMEOUT"),
        ):
            self.on_remove(event)

    def on_preinit(self, event):
        if event.alias_ip_address:
            self.address_provider.remove_dynamic_address(
                self.interface,
                ip_interface(event.alias_ip_address)
            )
        self.interface_provider.set_dynamic_config(self.interface, {"state": "up"})

    def on_update(self, event):
        # Remove address(es) if necessary
        if (
            event.alias_ip_address
            and event.alias_ip_address != event.old.ip_address
            and event.new.ip_address != event.old.ip_address
        ):
            self.address_provider.remove_dynamic_address(
                self.interface,
                ip_interface(event.alias_ip_address)
            )

        if event.old.ip_address and event.old.ip_address != event.new.ip_address:
            self.address_provider.remove_dynamic_address(
                self.interface,
                ip_interface(event.old.ip_address)
            )

        # Set MTU if given
        if event.new.mtu and event.new.mtu != event.old.mtu:
            self.interface_provider.set_dynamic_config(
                self.interface, {"state": "up", "mtu": event.new.mtu}
            )

        # Add address if new or changed
        if event.new.ip_address and event.new.ip_address != event.old.ip_address:
            self.address_provider.add_dynamic_address(
                self.interface,
                ip_interface(event.new.ip_address)
            )

        # Determine the ip networks
        if event.old.ip_address:
            old_network = ip_interface(event.old.ip_address).network
        else:
            old_network = None
        if event.new.ip_address:
            new_network = ip_interface(event.new.ip_address).network
        else:
            new_network = None

        # Add interface route if new or changed
        if event.new.ip_address and event.new.ip_address != event.old.ip_address:
            if event.old.ip_address:
                self.route_provider.remove_dynamic_route(
                    old_network, table=self.config.table
                )
            self.route_provider.add_dynamic_route(
                new_network,
                interface=self.interface,
                prefsrc=str(ip_interface(event.new.ip_address).ip),
                scope="link",
                table=self.config.table,
            )

        # Add or update gateway if given and within the ip network.
        old_gateway = None
        for gateway in event.old.gateway:
            if ip_address(gateway) in old_network:
                old_gateway = gateway
                break
        new_gateway = None
        for gateway in event.new.gateway:
            if ip_address(gateway) in new_network:
                new_gateway = gateway
                break
        if new_gateway and new_gateway != old_gateway:
            if old_gateway:
                self.route_provider.remove_dynamic_route(
                    ip_network("0.0.0.0/0"), table=self.config.table
                )
            self.route_provider.add_dynamic_route(
                ip_network("0.0.0.0/0"), gateway=new_gateway, table=self.config.table,
            )

        # Update routes
        old_routes = set()
        new_routes = set()
        for route in event.old.route:
            old_routes.add((route.destination, route.gateway))
        for route in event.new.route:
            new_routes.add((route.destination, route.gateway))
        for destination, gateway in old_routes - new_routes:
            self.route_provider.remove_dynamic_route(
                ip_network(destination), table=self.config.table
            )
        for destination, gateway in new_routes - old_routes:
            self.route_provider.add_dynamic_route(
                ip_network(destination), gateway=gateway, table=self.config.table
            )

    def on_remove(self, event):
        # Remove routes
        for route in event.old.route:
            self.route_provider.remove_dynamic_route(
                ip_network(route.destination), table=self.config.table
            )

        # Determine the ip networks
        if event.old.ip_address:
            old_network = ip_interface(event.old.ip_address).network
        else:
            old_network = None

        # Remove gateway
        for gateway in event.old.gateway:
            if ip_address(gateway) in old_network:
                self.route_provider.remove_dynamic_route(
                    ip_network("0.0.0.0/0"), table=self.config.table
                )
                break

        # Remove interface route
        if event.old.ip_address:
            self.route_provider.remove_dynamic_route(
                old_network, table=self.config.table
            )

        # Remove addresses
        if event.alias_ip_address and event.alias_ip_address != event.old.ip_address:
            self.address_provider.remove_dynamic_address(
                self.interface,
                ip_interface(event.alias_ip_address)
            )

        if event.old.ip_address:
            self.address_provider.remove_dynamic_address(
                self.interface,
                ip_interface(event.old.ip_address)
            )

        # Remove interface dynamic config
        if event.old.mtu:
            self.interface_provider.set_dynamic_config(self.interface, None)

    def start(self):
        logger.info("Starting DHCPv4 client on %s" % self.interface)
        self.systemd.manager.ReloadOrRestartUnit(self.unit, "replace")

    def stop(self):
        logger.info("Stopping DHCPv4 client on %s" % self.interface)
        self.systemd.manager.StopUnit(self.unit, "replace")
