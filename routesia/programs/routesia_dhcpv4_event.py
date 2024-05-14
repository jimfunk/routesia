#!/usr/bin/python3
#
# dhcpv4-event -- Routesia DHCPv4 event handler
#

import asyncio
import ipaddress
import logging
import os
import sys
from systemd.journal import JournalHandler

from routesia.service import Provider, Service
from routesia.mqtt import MQTT
from routesia.rpcclient import RPCClient
from routesia.schema.registry import SchemaRegistry

from routesia.schema.v1 import dhcp_client_pb2


logger = logging.getLogger("dhcp-event")


class DHCPEvent(Provider):
    def __init__(self, rpc: RPCClient, operation_timeout=5):
        super().__init__()
        self.rpc = rpc
        self.operation_timeout = operation_timeout

    def get_event(self):
        reason = os.environ["reason"]
        if reason not in dhcp_client_pb2.DHCPClientEventType.keys():
            logger.error(f"Unhandled event type {reason}")
            sys.exit(1)

        event = dhcp_client_pb2.DHCPv4ClientEvent()
        event.interface = os.environ["interface"]
        event.type = dhcp_client_pb2.DHCPClientEventType.Value(reason)
        if "medium" in os.environ:
            event.medium = os.environ["medium"]
        if "alias_ip_address" in os.environ:
            event.alias_ip_address = self.get_cidr_address(
                "alias_ip_address", "alias_subnet_mask"
            )

        if "new_ip_address" in os.environ:
            event.new.ip_address = self.get_cidr_address("new_ip_address", "new_subnet_mask")
        if "new_interface_mtu" in os.environ:
            event.new.mtu = int(os.environ["new_interface_mtu"])
        if "new_rfc3442_classless_static_routes_formatted" in os.environ:
            for route in self.get_rfc3442_routes(
                os.environ["new_rfc3442_classless_static_routes_formatted"]
            ):
                event.new.route.append(route)
        if "new_routers" in os.environ:
            for router in os.environ["new_routers"].split():
                event.new.gateway.append(router)
        if "new_domain_search" in os.environ:
            for domain in os.environ["new_domain_search"].split():
                event.new.domain_search.append(domain)
        if "new_domain_name" in os.environ:
            event.new.domain_name = os.environ["new_domain_name"]
        if "new_domain_name_servers" in os.environ:
            for server in os.environ["new_domain_name_servers"].split():
                event.new.domain_name_server.append(server)
        if "new_domain_ntp_servers" in os.environ:
            for server in os.environ["new_domain_ntp_servers"].split():
                event.new.ntp_server.append(server)
        if "new_dhcp_server_identifier" in os.environ:
            event.new.server_identifier = os.environ["new_dhcp_server_identifier"]

        if "old_ip_address" in os.environ:
            event.old.ip_address = self.get_cidr_address("old_ip_address", "old_subnet_mask")
        if "old_interface_mtu" in os.environ:
            event.old.mtu = int(os.environ["old_interface_mtu"])
        if "old_rfc3442_classless_static_routes_formatted" in os.environ:
            for destination, gateway in self.get_rfc3442_routes(
                os.environ["old_rfc3442_classless_static_routes_formatted"]
            ):
                route = event.old.route.add()
                route.destination = destination
                route.gateway = gateway
        if "old_routers" in os.environ:
            for router in os.environ["old_routers"].split():
                event.old.gateway.append(router)
        if "old_domain_search" in os.environ:
            for domain in os.environ["old_domain_search"].split():
                event.old.domain_search.append(domain)
        if "old_domain_name" in os.environ:
            event.old.domain_name = os.environ["old_domain_name"]
        if "old_domain_name_servers" in os.environ:
            for server in os.environ["old_domain_name_servers"].split():
                event.old.domain_name_server.append(server)
        if "old_domain_ntp_servers" in os.environ:
            for server in os.environ["old_domain_ntp_servers"].split():
                event.old.ntp_server.append(server)
        if "old_dhcp_server_identifier" in os.environ:
            event.old.server_identifier = os.environ["old_dhcp_server_identifier"]

        return event

    def get_cidr_address(self, ip_var, mask_var):
        "Get a CIDR formatted address from the given environment variables"
        address = ipaddress.ip_address(os.environ[ip_var])

        mask = os.environ.get(mask_var)
        if not mask:
            mask = "32" if address.version == 4 else "128"

        return str(ipaddress.ip_interface("%s/%s" % (address, mask)))

    def get_rfc3442_routes(self, value):
        routes = []
        octets = [int(octet) for octet in value.split()]
        while octets:
            prefix_length = octets.pop(0)
            num_prefix_octets = int(prefix_length / 8)
            num_trailing_octets = 4 - num_prefix_octets
            route_octets = []
            for _ in range(num_prefix_octets):
                route_octets.append(octets.pop(0))
            for _ in range(num_trailing_octets):
                route_octets.append(0)
            destination = "%s/%s" % (".".join(route_octets), prefix_length)
            gateway_octets = []
            for _ in range(4):
                gateway_octets.append(octets.pop(0))
            gateway = ".".join(gateway_octets)
            routes.append((destination, gateway))
        return routes

    async def main(self):
        if "reason" not in os.environ:
            print("No reason in environment. Must be called from dhclient", file=sys.stderr)
            return 1

        event = self.get_event()

        try:
            async with asyncio.timeout(self.operation_timeout):
                await self.rpc.wait_connect()
        except TimeoutError:
            logger.error("Timed out connecting to agent")
            return 1

        if event:
            logger.info("Sending event to agent")
            try:
                async with asyncio.timeout(self.operation_timeout):
                    await self.rpc.request("dhcp/client/v4/event", event)
            except TimeoutError:
                logger.error("Timed out sending event")
                return 1

        return 0

async def run() -> int:
    handler = JournalHandler()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    service = Service()
    service.add_provider(DHCPEvent)
    service.add_provider(MQTT)
    service.add_provider(RPCClient, prefix="routesia/agent/rpc")
    service.add_provider(SchemaRegistry)

    await service.start_background()
    eventprovider = await service.get_provider(DHCPEvent)
    ret = await eventprovider.main()
    await service.stop_background()
    return ret


def main():
    try:
        sys.exit(asyncio.run(run()))
    except KeyboardInterrupt:
        pass
