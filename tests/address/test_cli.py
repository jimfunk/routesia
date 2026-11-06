from routesia.address.cli import AddressCLI
from routesia.schema.v1 import address_pb2


class FakeRPC:
    def __init__(self, addresses):
        self.addresses = addresses

    async def request(self, method, argument=None):
        if method == "address/list":
            return self.addresses
        raise AssertionError(f"Unexpected RPC method: {method}")


async def test_show_addresses(cli):
    addresses = address_pb2.AddressList()
    eth0 = addresses.address.add()
    eth0.address.interface = "eth0"
    eth0.address.ip = "192.0.2.1/24"
    eth1 = addresses.address.add()
    eth1.address.interface = "eth1"
    eth1.address.ip = "198.51.100.1/24"

    AddressCLI(cli, FakeRPC(addresses))

    result = await cli.handle_command("address show")
    assert [address.address.interface for address in result.address] == [
        "eth0",
        "eth1",
    ]

    result = await cli.handle_command("address show interface eth0")
    assert [address.address.interface for address in result.address] == ["eth0"]
