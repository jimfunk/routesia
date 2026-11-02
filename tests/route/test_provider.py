"""
tests/route/test_provider.py
"""

from ipaddress import ip_address, ip_interface

from routesia.dhcp.client.events import DHCPv4LeaseAcquired
from routesia.route.provider import RouteProvider


class FakeTable:
    def __init__(self):
        self.leases = []

    def handle_dhcp_lease_acquired(self, event):
        self.leases.append(event)


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
