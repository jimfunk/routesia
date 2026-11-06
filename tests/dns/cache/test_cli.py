import pytest

from routesia.cli import InvalidArgument
from routesia.dns.cache.cli import DNSCacheCLI
from routesia.schema.v1 import dns_cache_pb2


class FakeRPC:
    def __init__(self, config):
        self.config = config
        self.updated = None

    async def request(self, method, argument=None):
        if method == "dns/cache/config/get":
            return self.config
        if method == "dns/cache/config/update":
            self.updated = argument
            return None
        raise AssertionError(f"Unexpected RPC method: {method}")


async def test_add_listen_address_duplicate(cli):
    config = dns_cache_pb2.DNSCacheConfig()
    listen_address = config.listen_address.add()
    listen_address.address = "192.0.2.1"
    listen_address.port = 53
    rpc = FakeRPC(config)
    DNSCacheCLI(cli, rpc)

    with pytest.raises(InvalidArgument, match="Listen address already exists"):
        await cli.handle_command(
            "dns cache config listen-address add 192.0.2.1 listen-port 53"
        )

    assert rpc.updated is None
