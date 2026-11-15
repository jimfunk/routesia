from routesia.interface.cli import InterfaceCLI
from routesia.schema.v1 import interface_pb2


class FakeRPC:
    def __init__(self, interfaces=None):
        self.interfaces = interfaces or interface_pb2.InterfaceConfigList()
        self.added = None
        self.updated = None

    async def request(self, method, argument=None):
        if method == "interface/config/add":
            self.added = argument
            return None
        if method == "interface/config/list":
            return self.interfaces
        if method == "interface/config/update":
            self.updated = argument
            return None
        raise AssertionError(f"Unexpected RPC method: {method}")


async def test_add_interface_mss_clamp(cli):
    rpc = FakeRPC()
    InterfaceCLI(cli, rpc)

    await cli.handle_command(
        "interface config add eth0 mss_clamp.mtu 1492 mss_clamp.family IPV6"
    )

    assert rpc.added.mss_clamp.mtu == 1492
    assert rpc.added.mss_clamp.family == interface_pb2.MSSClamp.IPV6


async def test_add_interface_mss_clamp_defaults_to_all_families(cli):
    rpc = FakeRPC()
    InterfaceCLI(cli, rpc)

    await cli.handle_command("interface config add eth0 mss_clamp.mtu 1492")

    assert rpc.added.mss_clamp.family == interface_pb2.MSSClamp.ALL


async def test_update_interface_mss_clamp(cli):
    interfaces = interface_pb2.InterfaceConfigList()
    interfaces.interface.add().name = "eth0"
    rpc = FakeRPC(interfaces)
    InterfaceCLI(cli, rpc)

    await cli.handle_command(
        "interface config update eth0 mss_clamp.mtu 1472 mss_clamp.family IPV4"
    )

    assert rpc.updated.mss_clamp.mtu == 1472
    assert rpc.updated.mss_clamp.family == interface_pb2.MSSClamp.IPV4


async def test_complete_mss_clamp_family(cli):
    InterfaceCLI(cli, FakeRPC())

    completions = await cli.router.get_command_completions(
        ["interface", "config", "add", "eth0", "mss_clamp.family"]
    )

    assert completions == ["ALL", "IPV4", "IPV6"]


async def test_add_pppoe_interface(cli):
    rpc = FakeRPC()
    InterfaceCLI(cli, rpc)

    await cli.handle_command(
        "interface config add pppoe0 type PPPOE "
        "pppoe.interface eth0 "
        "pppoe.username user@example.com "
        "pppoe.password secret "
        "pppoe.mtu 1508 "
        "pppoe.address_mode IPV4 "
        "pppoe.ipv6_interface_id PERSISTENT "
        "pppoe.table 100"
    )

    assert rpc.added.type == interface_pb2.PPPOE
    assert rpc.added.pppoe.interface == "eth0"
    assert rpc.added.pppoe.username == "user@example.com"
    assert rpc.added.pppoe.password == "secret"
    assert rpc.added.pppoe.mtu == 1508
    assert rpc.added.pppoe.address_mode == interface_pb2.IPV4
    assert (
        rpc.added.pppoe.ipv6_interface_id
        == interface_pb2.PPPoEInterfaceConfig.PERSISTENT
    )
    assert rpc.added.pppoe.table == 100


async def test_update_pppoe_interface(cli):
    interfaces = interface_pb2.InterfaceConfigList()
    interface = interfaces.interface.add()
    interface.name = "pppoe0"
    interface.type = interface_pb2.PPPOE
    interface.pppoe.interface = "eth0"
    interface.pppoe.username = "user"
    interface.pppoe.password = "secret"
    rpc = FakeRPC(interfaces)
    InterfaceCLI(cli, rpc)

    await cli.handle_command(
        "interface config update pppoe0 pppoe.password newsecret pppoe.address_mode IPV6"
    )

    assert rpc.updated.pppoe.password == "newsecret"
    assert rpc.updated.pppoe.address_mode == interface_pb2.IPV6
    assert rpc.updated.pppoe.interface == "eth0"


async def test_complete_address_mode(cli):
    InterfaceCLI(cli, FakeRPC())

    completions = await cli.router.get_command_completions(
        ["interface", "config", "add", "pppoe0", "pppoe.address_mode"]
    )

    assert completions == ["ANY", "IPV4", "IPV6", "NONE"]
