"""
tests/route/test_entities.py
"""

import errno
from ipaddress import ip_address, ip_interface, ip_network
from types import SimpleNamespace

import pytest
from pyroute2 import NetlinkError

from routesia.dhcp.client.events import DHCPv4LeaseAcquired
from routesia.route.entities import PROTO_ID, RT_SCOPE_LINK, TableEntity


class FakeIPRoute:
    def __init__(self):
        self.routes = []
        self.error = None

    def route(self, cmd, **kwargs):
        if self.error:
            raise self.error
        if cmd in ("replace", "delete"):
            self.routes = [
                route for route in self.routes if route["dst"] != kwargs["dst"]
            ]
        if cmd == "replace":
            self.routes.append(kwargs)


class FakeIPRouteProvider:
    def __init__(self):
        self.iproute = FakeIPRoute()
        self.interface_name_map = {"eth0": 2, "pppoe0": 3}


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


def make_pppoe_table():
    table, iproute = make_table()
    table.handle_interface_add(SimpleNamespace(ifname="pppoe0"))
    return table, iproute


def test_pppoe_link_up_installs_default_route():
    table, iproute = make_pppoe_table()

    table.handle_pppoe_link_up("pppoe0", 4)

    assert iproute.routes == [
        {
            "table": 254,
            "dst": "0.0.0.0/0",
            "proto": PROTO_ID,
            "oif": 3,
            "scope": RT_SCOPE_LINK,
        }
    ]


def test_pppoe_ipv6_link_up_installs_default_route():
    table, iproute = make_pppoe_table()

    table.handle_pppoe_link_up("pppoe0", 6)

    assert iproute.routes == [
        {
            "table": 254,
            "dst": "::/0",
            "proto": PROTO_ID,
            "oif": 3,
            "scope": RT_SCOPE_LINK,
        }
    ]


def test_pppoe_link_up_is_idempotent():
    table, iproute = make_pppoe_table()

    table.handle_pppoe_link_up("pppoe0", 4)
    table.handle_pppoe_link_up("pppoe0", 4)

    assert len(iproute.routes) == 1


def test_pppoe_link_down_removes_default_route():
    table, iproute = make_pppoe_table()
    table.handle_pppoe_link_up("pppoe0", 4)

    table.handle_pppoe_link_down("pppoe0", 4)

    assert iproute.routes == []
    assert "pppoe0" not in table.dynamic_routes


def test_pppoe_link_down_leaves_other_routes():
    table, iproute = make_pppoe_table()
    table.handle_pppoe_link_up("pppoe0", 4)
    table.handle_pppoe_link_up("pppoe0", 6)

    table.handle_pppoe_link_down("pppoe0", 4)

    assert destinations(iproute) == ["::/0"]


def test_pppoe_link_down_tolerates_route_already_removed():
    table, iproute = make_pppoe_table()
    table.handle_pppoe_link_up("pppoe0", 4)
    iproute.error = NetlinkError(errno.ESRCH, "No such process")

    table.handle_pppoe_link_down("pppoe0", 4)

    assert "pppoe0" not in table.dynamic_routes


def test_route_removal_reraises_unexpected_errors():
    table, iproute = make_pppoe_table()
    table.handle_pppoe_link_up("pppoe0", 4)
    iproute.error = NetlinkError(errno.EPERM, "Operation not permitted")

    with pytest.raises(NetlinkError):
        table.handle_pppoe_link_down("pppoe0", 4)


def test_pppoe_route_add_is_retried_when_link_is_not_ready():
    table, iproute = make_pppoe_table()
    iproute.error = NetlinkError(errno.ENETDOWN, "Network is down")

    table.handle_pppoe_link_up("pppoe0", 4)

    route = table.dynamic_routes["pppoe0"][ip_network("0.0.0.0/0")]
    assert route.route_args is None

    iproute.error = None
    table.handle_interface_add(SimpleNamespace(ifname="pppoe0"))

    assert route.route_args["dst"] == "0.0.0.0/0"
