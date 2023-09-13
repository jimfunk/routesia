#!/usr/bin/python3
#
# dhcpv4-event -- Routesia DHCPv4 event handler
#

import ipaddress
import os
import sys

from routesia.rpcclient import RPCClient
from routesia.schema.v1 import dhcpclient_pb2


def get_cidr_address(ip_var, mask_var):
    "Get a CIDR formatted address from the given environment variables"
    address = ipaddress.ip_address(os.environ[ip_var])

    mask = os.environ.get(mask_var)
    if not mask:
        mask = "32" if address.version == 4 else "128"

    return str(ipaddress.ip_interface("%s/%s" % (address, mask)))


def get_rfc3442_routes(value):
    routes = []
    octets = [int(octet) for octet in value.split()]
    while octets:
        prefix_length = octets.pop(0)
        num_prefix_octets = int(prefix_length / 8)
        num_trailing_octets = 4 - num_prefix_octets
        route_octets = []
        for i in range(num_prefix_octets):
            route_octets.append(octets.pop(0))
        for i in range(num_trailing_octets):
            route_octets.append(0)
        destination = "%s/%s" % (".".join(route_octets), prefix_length)
        gateway_octets = []
        for i in range(4):
            gateway_octets.append(octets.pop(0))
        gateway = ".".join(gateway_octets)
        routes.append((destination, gateway))
    return routes


def get_event():
    reason = os.environ["reason"]
    if reason not in dhcpclient_pb2.DHCPClientEventType.keys():
        print("Unhandled event type %s" % reason)
        return

    event = dhcpclient_pb2.DHCPv4ClientEvent()
    event.interface = os.environ["interface"]
    event.type = dhcpclient_pb2.DHCPClientEventType.Value(reason)
    if "medium" in os.environ:
        event.medium = os.environ["medium"]
    if "alias_ip_address" in os.environ:
        event.alias_ip_address = get_cidr_address(
            "alias_ip_address", "alias_subnet_mask"
        )

    if "new_ip_address" in os.environ:
        event.new.ip_address = get_cidr_address("new_ip_address", "new_subnet_mask")
    if "new_interface_mtu" in os.environ:
        event.new.mtu = int(os.environ["new_interface_mtu"])
    if "new_rfc3442_classless_static_routes_formatted" in os.environ:
        for route in get_rfc3442_routes(
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
        event.old.ip_address = get_cidr_address("old_ip_address", "old_subnet_mask")
    if "old_interface_mtu" in os.environ:
        event.old.mtu = int(os.environ["old_interface_mtu"])
    if "old_rfc3442_classless_static_routes_formatted" in os.environ:
        for destination, gateway in get_rfc3442_routes(
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


if __name__ == "__main__":
    if "reason" not in os.environ:
        print("No reason in environment. Must be called from dhclient")
        sys.exit(1)

    event = get_event()

    if event:
        client = RPCClient()
        client.connect()
        client.request("/dhcp/client/v4/event", event)
        client.run_until_complete()
