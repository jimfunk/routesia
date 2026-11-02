"""
tests/route/test_entities.py
"""

from ipaddress import ip_address, ip_interface
from types import SimpleNamespace

from routesia.dhcp.client.events import DHCPv4LeaseAcquired
from routesia.route.entities import TableEntity


class FakeIPRoute:
    def __init__(self):
        self.routes = []

    def route(self, cmd, **kwargs):
        if cmd in ("replace", "delete"):
            self.routes = [
                route for route in self.routes if route["dst"] != kwargs["dst"]
            ]
        if cmd == "replace":
            self.routes.append(kwargs)


class FakeIPRouteProvider:
    def __init__(self):
        self.iproute = FakeIPRoute()
        self.interface_name_map = {"eth0": 2}


def make_table():
    iproute = FakeIPRouteProvider()
    table = TableEntity(iproute, 254, "main")
    return table, iproute.iproute


def make_lease(address="192.168.1.10/24", gateway="192.168.1.1"):
    return DHCPv4LeaseAcquired(
        interface="eth0",
        table=0,
        address=ip_interface(address),
        gateway=ip_address(gateway),
        routes=[],
        mtu=1500,
        domain_name="",
        domain_name_servers=[],
        search_domains=[],
        ntp_servers=[],
        server_identifier=ip_address("192.168.1.254"),
    )


def destinations(iproute):
    return [route["dst"] for route in iproute.routes]


def test_dhcp_lease_installs_subnet_then_default_route():
    table, iproute = make_table()
    table.handle_interface_add(SimpleNamespace(ifname="eth0"))

    table.handle_dhcp_lease_acquired(make_lease())

    assert destinations(iproute) == ["192.168.1.0/24", "0.0.0.0/0"]


def test_dhcp_lease_replaces_changed_routes():
    table, iproute = make_table()
    table.handle_interface_add(SimpleNamespace(ifname="eth0"))
    table.handle_dhcp_lease_acquired(make_lease())

    iproute.routes.clear()
    table.handle_dhcp_lease_acquired(
        make_lease(address="192.168.2.10/24", gateway="192.168.2.1")
    )

    assert destinations(iproute) == ["192.168.2.0/24", "0.0.0.0/0"]
    assert iproute.routes[1]["gateway"] == "192.168.2.1"


def test_dhcp_default_route_installed_when_interface_appears():
    table, iproute = make_table()
    table.handle_dhcp_lease_acquired(make_lease())

    assert destinations(iproute) == ["192.168.1.0/24"]

    table.handle_interface_add(SimpleNamespace(ifname="eth0"))

    assert destinations(iproute) == ["192.168.1.0/24", "0.0.0.0/0"]
