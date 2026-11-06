import pytest

from routesia.cli import InvalidArgument
from routesia.dns.authoritative.cli import DNSAuthoritativeCLI
from routesia.schema.v1 import dns_authoritative_pb2


class FakeRPC:
    def __init__(self, config):
        self.config = config
        self.updated = None

    async def request(self, method, argument=None):
        if method == "dns/authoritative/config/get":
            return self.config
        if method == "dns/authoritative/config/update":
            self.updated = argument
            return None
        raise AssertionError(f"Unexpected RPC method: {method}")


async def test_add_listen_address_ipv4(cli):
    config = dns_authoritative_pb2.AuthoritativeDNSConfig()
    rpc = FakeRPC(config)
    DNSAuthoritativeCLI(cli, rpc)

    await cli.handle_command(
        "dns authoritative config listen-address add 192.0.2.1 listen-port 53"
    )

    assert len(rpc.config.listen_address) == 1
    assert rpc.config.listen_address[0].address == "192.0.2.1"
    assert rpc.config.listen_address[0].port == 53
    assert rpc.updated is rpc.config


async def test_add_listen_address_ipv6(cli):
    config = dns_authoritative_pb2.AuthoritativeDNSConfig()
    rpc = FakeRPC(config)
    DNSAuthoritativeCLI(cli, rpc)

    await cli.handle_command(
        "dns authoritative config listen-address add 2001:db8::1"
    )

    assert len(rpc.config.listen_address) == 1
    assert rpc.config.listen_address[0].address == "2001:db8::1"
    assert rpc.config.listen_address[0].port == 0
    assert rpc.updated is rpc.config


async def test_add_listen_address_duplicate(cli):
    config = dns_authoritative_pb2.AuthoritativeDNSConfig()
    listen_address = config.listen_address.add()
    listen_address.address = "192.0.2.1"
    listen_address.port = 53
    rpc = FakeRPC(config)
    DNSAuthoritativeCLI(cli, rpc)

    with pytest.raises(InvalidArgument, match="Listen address already exists"):
        await cli.handle_command(
            "dns authoritative config listen-address add 192.0.2.1 listen-port 53"
        )

    assert rpc.updated is None
