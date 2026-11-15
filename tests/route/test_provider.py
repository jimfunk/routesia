"""
tests/route/test_provider.py
"""

from ipaddress import ip_address, ip_interface

from routesia.dhcp.client.events import DHCPv4LeaseAcquired
from routesia.interface.events import PPPoELinkDown, PPPoELinkUp
from routesia.route.provider import RouteProvider


class FakeTable:
    def __init__(self):
        self.leases = []
        self.pppoe_links = []

    def handle_dhcp_lease_acquired(self, event):
        self.leases.append(event)

    def handle_pppoe_link_up(self, interface, family):
        self.pppoe_links.append((interface, family))

    def handle_pppoe_link_down(self, interface, family):
        self.pppoe_links.append((interface, family))


async def test_dhcp_lease_acquired_uses_configured_table():
    provider = RouteProvider.__new__(RouteProvider)
    main = FakeTable()
    custom = FakeTable()
    provider.tables = {254: main, 100: custom}

    event = DHCPv4LeaseAcquired(
        interface="eth0",
        table=100,
        address=ip_interface("192.168.1.10/24"),
        gateway=ip_address("192.168.1.1"),
        routes=[],
        mtu=1500,
        domain_name="",
        domain_name_servers=[],
        search_domains=[],
        ntp_servers=[],
        server_identifier=ip_address("192.168.1.254"),
    )
    await provider.handle_dhcp_lease_acquired(event)

    assert custom.leases == [event]
    assert main.leases == []


async def test_pppoe_link_up_uses_configured_table():
    provider = RouteProvider.__new__(RouteProvider)
    main = FakeTable()
    custom = FakeTable()
    provider.tables = {254: main, 100: custom}

    await provider.handle_pppoe_link_up(
        PPPoELinkUp(interface="pppoe0", table=100, family=4)
    )

    assert custom.pppoe_links == [("pppoe0", 4)]
    assert main.pppoe_links == []


async def test_pppoe_link_up_uses_main_table_by_default():
    provider = RouteProvider.__new__(RouteProvider)
    main = FakeTable()
    provider.tables = {254: main}

    await provider.handle_pppoe_link_up(
        PPPoELinkUp(interface="pppoe0", table=0, family=4)
    )

    assert main.pppoe_links == [("pppoe0", 4)]


async def test_pppoe_link_down_uses_configured_table():
    provider = RouteProvider.__new__(RouteProvider)
    main = FakeTable()
    custom = FakeTable()
    provider.tables = {254: main, 100: custom}

    await provider.handle_pppoe_link_down(
        PPPoELinkDown(interface="pppoe0", table=100, family=6)
    )

    assert custom.pppoe_links == [("pppoe0", 6)]
    assert main.pppoe_links == []
