"""
routesia/dhcp/client/entities.py - DHCP client entities
"""

from ipaddress import ip_address, ip_interface, ip_network
import logging

from routesia.dhcp.dhcpclientevents import (
    DHCPv4LeasePreinit,
    DHCPv4LeaseAcquired,
    DHCPv4LeaseLost,
    DHCPv4Route,
)
from routesia.schema.v2.dhcp_client_pb2 import (
    DHCPClientEventType,
    DHCPv4ClientEvent,
    DHCPv4ClientStatus,
)
from routesia.service import Service


logger = logging.getLogger("dhcp-client")


class DHCPv4Client:
    def __init__(self, systemd, config, service: Service):
        self.systemd = systemd
        self.config = config
        self.service = service
        self.interface = config.interface
        self.status = DHCPv4ClientStatus()
        self.status.interface = self.interface

    @property
    def unit(self):
        return "routesia-dhcpv4-client@%s.service" % self.interface

    def handle_config_change(self, config):
        old_config = self.config
        self.config = config
        if old_config is None:
            self.start()
        elif old_config.SerializeToString() != self.config.SerializeToString():
            if (
                old_config.interface != self.config.interface
                or old_config.table != self.config.table
            ):
                self.stop()
                self.interface = self.config.interface
                self.start()
            else:
                self.start()

    async def on_event(self, event: DHCPv4ClientEvent):
        self.status.last_event.CopyFrom(event)

        routes = []
        for route in event.new.route:
            routes.append(
                DHCPv4Route(
                    destination=ip_network(route.destination),
                    gateway=ip_address(route.gateway),
                )
            )
        alias_ip_address = (
            ip_interface(event.alias_ip_address) if event.alias_ip_address else None
        )
        address = ip_interface(event.new.ip_address) if event.new.ip_address else None
        gateway = ip_address(event.new.gateway[0]) if event.new.gateway else None
        domain_name_servers = [
            ip_address(server) for server in event.new.domain_name_server
        ]
        ntp_servers = [ip_address(server) for server in event.new.ntp_server]

        if event.type == DHCPClientEventType.PREINIT:
            self.service.publish_event(
                DHCPv4LeasePreinit(
                    interface=self.interface,
                    table=self.config.table,
                    address=alias_ip_address,
                )
            )
        elif event.type in (
            DHCPClientEventType.BOUND,
            DHCPClientEventType.RENEW,
            DHCPClientEventType.REBIND,
            DHCPClientEventType.REBOOT,
        ):
            self.service.publish_event(
                DHCPv4LeaseAcquired(
                    interface=self.interface,
                    table=self.config.table,
                    address=address,
                    gateway=gateway,
                    routes=routes,
                    mtu=event.new.mtu,
                    domain_name=event.new.domain_name,
                    domain_name_servers=domain_name_servers,
                    search_domains=event.new.domain_search,
                    ntp_servers=ntp_servers,
                    server_identifier=event.new.server_identifier,
                )
            )
        elif event.type in (
            DHCPClientEventType.EXPIRE,
            DHCPClientEventType.FAIL,
            DHCPClientEventType.RELEASE,
            DHCPClientEventType.STOP,
            DHCPClientEventType.TIMEOUT,
        ):
            self.service.publish_event(
                DHCPv4LeaseLost(
                    interface=self.interface,
                    table=self.config.table,
                    address=address,
                    gateway=gateway,
                    routes=routes,
                    mtu=event.new.mtu,
                    domain_name=event.new.domain_name,
                    domain_name_servers=domain_name_servers,
                    search_domains=event.new.domain_search,
                    ntp_servers=ntp_servers,
                    server_identifier=event.new.server_identifier,
                )
            )

    def start(self):
        logger.info("Starting DHCPv4 client on %s" % self.interface)
        self.systemd.start_unit(self.unit)

    def stop(self):
        logger.info("Stopping DHCPv4 client on %s" % self.interface)
        self.systemd.stop_unit(self.unit)
