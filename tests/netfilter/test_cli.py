import pytest

from routesia.cli.exceptions import InvalidArgument
from routesia.netfilter.cli import NetfilterCLI
from routesia.schema.v1 import netfilter_pb2


class FakeRPC:
    def __init__(self, config):
        self.config = config
        self.updated = None

    async def request(self, method, argument=None):
        if method == "netfilter/config/get":
            return self.config
        if method == "netfilter/config/update":
            self.updated = argument
            return None
        raise AssertionError(f"Unexpected RPC method: {method}")


async def test_add_input_rule_ip_protocol(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.input.rule.add().ip.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule ip-match protocol add 0 0 tcp"
    )

    assert list(rpc.config.input.rule[0].ip[0].protocol) == ["tcp"]
    assert rpc.updated is rpc.config


async def test_add_forward_rule_ip_protocol(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.forward.rule.add().ip.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config forward rule ip-match protocol add 0 0 udp"
    )

    assert list(rpc.config.forward.rule[0].ip[0].protocol) == ["udp"]
    assert rpc.updated is rpc.config


async def test_list_input_rule_ct_match(cli):
    config = netfilter_pb2.NetfilterConfig()
    rule = config.input.rule.add()
    rule.ct.add().state.append("new")
    rule.ct.add().state.append("established")
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    result = await cli.handle_command(
        "netfilter config input rule ct-match list 0"
    )

    assert result == '0:\n    state: "new"\n1:\n    state: "established"\n'


async def test_list_forward_rule_ct_match(cli):
    config = netfilter_pb2.NetfilterConfig()
    rule = config.forward.rule.add()
    rule.ct.add().state.append("new")
    rule.ct.add().state.append("established")
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    result = await cli.handle_command(
        "netfilter config forward rule ct-match list 0"
    )

    assert result == '0:\n    state: "new"\n1:\n    state: "established"\n'


async def test_add_input_rule_meta_match_input_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.input.rule.add().meta.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule meta-match input-interface add 0 0 eth0"
    )

    assert list(rpc.config.input.rule[0].meta[0].input_interface) == ["eth0"]
    assert rpc.updated is rpc.config


async def test_remove_input_rule_meta_match_input_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.input.rule.add().meta.add()
    match.input_interface.extend(["eth0", "eth1"])
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule meta-match input-interface remove 0 0 eth0"
    )

    assert list(rpc.config.input.rule[0].meta[0].input_interface) == ["eth1"]
    assert rpc.updated is rpc.config


async def test_add_forward_rule_meta_match_input_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.forward.rule.add().meta.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config forward rule meta-match input-interface add 0 0 eth0"
    )

    assert list(rpc.config.forward.rule[0].meta[0].input_interface) == ["eth0"]
    assert rpc.updated is rpc.config


async def test_remove_forward_rule_meta_match_input_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.forward.rule.add().meta.add()
    match.input_interface.extend(["eth0", "eth1"])
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config forward rule meta-match input-interface remove 0 0 eth0"
    )

    assert list(rpc.config.forward.rule[0].meta[0].input_interface) == ["eth1"]
    assert rpc.updated is rpc.config


async def test_add_forward_rule_meta_match_output_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.forward.rule.add().meta.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config forward rule meta-match output-interface add 0 0 eth1"
    )

    assert list(rpc.config.forward.rule[0].meta[0].output_interface) == ["eth1"]
    assert rpc.updated is rpc.config


async def test_remove_forward_rule_meta_match_output_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.forward.rule.add().meta.add()
    match.output_interface.extend(["eth0", "eth1"])
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config forward rule meta-match output-interface remove 0 0 eth0"
    )

    assert list(rpc.config.forward.rule[0].meta[0].output_interface) == ["eth1"]
    assert rpc.updated is rpc.config


async def test_update_forward_rule_icmp_match(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.forward.rule.add().icmp.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config forward rule icmp-match update 0 0 "
        "type echo-request code 8 negate true"
    )

    match = rpc.config.forward.rule[0].icmp[0]
    assert list(match.type) == ["echo-request"]
    assert list(match.code) == [8]
    assert match.negate is True
    assert rpc.updated is rpc.config


async def test_masquerade_ip_forward_port_protocol_completion(cli):
    NetfilterCLI(cli, FakeRPC(netfilter_pb2.NetfilterConfig()))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "masquerade",
            "ip-forward-port",
            "add",
            "eth0",
            "10.0.0.1",
        ]
    )

    assert completions == ["TCP", "UDP", "SCTP"]


async def test_masquerade_ip_forward_port_remove_protocol_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "10.0.0.1"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.IPForwardProtocol.TCP
    port_map.port = "80"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.IPForwardProtocol.UDP
    port_map.port = "53"
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "masquerade",
            "ip-forward-port",
            "remove",
            "eth0",
            "10.0.0.1",
        ]
    )

    assert completions == ["TCP", "UDP"]


async def test_masquerade_ip_forward_port_remove_port_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "10.0.0.1"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.IPForwardProtocol.TCP
    port_map.port = "80"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.IPForwardProtocol.TCP
    port_map.port = "443"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.IPForwardProtocol.UDP
    port_map.port = "53"
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "masquerade",
            "ip-forward-port",
            "remove",
            "eth0",
            "10.0.0.1",
            "TCP",
        ]
    )

    assert completions == ["80", "443"]


async def test_input_rule_ip_match_protocol_remove_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.input.rule.add().ip.add()
    match.protocol.extend(["tcp", "udp"])
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "input",
            "rule",
            "ip-match",
            "protocol",
            "remove",
            "0",
            "0",
        ]
    )

    assert completions == ["tcp", "udp"]


async def test_input_rule_ip6_match_protocol_remove_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.input.rule.add().ip6.add()
    match.protocol.extend(["tcp", "udp"])
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "input",
            "rule",
            "ip6-match",
            "protocol",
            "remove",
            "0",
            "0",
        ]
    )

    assert completions == ["tcp", "udp"]


async def test_input_rule_meta_match_protocol_remove_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.input.rule.add().meta.add()
    match.protocol.extend(["tcp", "udp"])
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "input",
            "rule",
            "meta-match",
            "protocol",
            "remove",
            "0",
            "0",
        ]
    )

    assert completions == ["tcp", "udp"]


async def test_forward_rule_ip_match_protocol_remove_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.forward.rule.add().ip.add()
    match.protocol.extend(["tcp", "udp"])
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "forward",
            "rule",
            "ip-match",
            "protocol",
            "remove",
            "0",
            "0",
        ]
    )

    assert completions == ["tcp", "udp"]


async def test_forward_rule_ip6_match_protocol_remove_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.forward.rule.add().ip6.add()
    match.protocol.extend(["tcp", "udp"])
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "forward",
            "rule",
            "ip6-match",
            "protocol",
            "remove",
            "0",
            "0",
        ]
    )

    assert completions == ["tcp", "udp"]


async def test_forward_rule_meta_match_protocol_remove_completion(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.forward.rule.add().meta.add()
    match.protocol.extend(["tcp", "udp"])
    NetfilterCLI(cli, FakeRPC(config))

    completions = await cli.router.get_command_completions(
        [
            "netfilter",
            "config",
            "forward",
            "rule",
            "meta-match",
            "protocol",
            "remove",
            "0",
            "0",
        ]
    )

    assert completions == ["tcp", "udp"]


async def test_update_input_rule_meta_match(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.input.rule.add().meta.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule meta-match update 0 0 "
        "input-interface eth0 protocol tcp negate true"
    )

    match = rpc.config.input.rule[0].meta[0]
    assert list(match.input_interface) == ["eth0"]
    assert list(match.protocol) == ["tcp"]
    assert match.negate is True
    assert rpc.updated is rpc.config


async def test_remove_input_rule_meta_match(cli):
    config = netfilter_pb2.NetfilterConfig()
    rule = config.input.rule.add()
    rule.meta.add()
    rule.meta.add().protocol.append("tcp")
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule meta-match remove 0 0"
    )

    assert len(rpc.config.input.rule[0].meta) == 1
    assert list(rpc.config.input.rule[0].meta[0].protocol) == ["tcp"]
    assert rpc.updated is rpc.config


async def test_add_input_rule_meta_protocol(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.input.rule.add().meta.add()
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule meta-match protocol add 0 0 tcp"
    )

    assert list(rpc.config.input.rule[0].meta[0].protocol) == ["tcp"]
    assert rpc.updated is rpc.config


async def test_remove_input_rule_meta_protocol(cli):
    config = netfilter_pb2.NetfilterConfig()
    match = config.input.rule.add().meta.add()
    match.protocol.extend(["tcp", "udp"])
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config input rule meta-match protocol remove 0 0 tcp"
    )

    assert list(rpc.config.input.rule[0].meta[0].protocol) == ["udp"]
    assert rpc.updated is rpc.config


async def test_add_masquerade_default_family(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config masquerade add eth0")

    assert rpc.config.masquerade[0].interface == "eth0"
    assert rpc.config.masquerade[0].family == netfilter_pb2.IPV4
    assert rpc.updated is rpc.config


async def test_add_masquerade_ipv6(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config masquerade add eth0 family IPV6")

    assert rpc.config.masquerade[0].family == netfilter_pb2.IPV6


async def test_add_masquerade_same_interface_both_families(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config masquerade add eth0")
    await cli.handle_command("netfilter config masquerade add eth0 family IPV6")

    assert len(rpc.config.masquerade) == 2


async def test_add_masquerade_duplicate_family(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config masquerade add eth0")

    with pytest.raises(InvalidArgument):
        await cli.handle_command("netfilter config masquerade add eth0")


async def test_remove_masquerade_ipv6_only(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    masquerade.family = netfilter_pb2.IPV6
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command("netfilter config masquerade remove eth0")

    assert len(rpc.config.masquerade) == 1

    await cli.handle_command("netfilter config masquerade remove eth0 family IPV6")

    assert len(rpc.config.masquerade) == 0


async def test_add_masquerade_forward_ipv6(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    masquerade.family = netfilter_pb2.IPV6
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config masquerade ip-forward add eth0 2001:db8::2 family IPV6"
    )

    assert rpc.config.masquerade[0].ip_forward[0].destination == "2001:db8::2"


async def test_add_masquerade_forward_requires_existing_masquerade(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command(
            "netfilter config masquerade ip-forward add eth0 192.0.2.10"
        )


async def test_add_masquerade_port_same_destination_port(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "192.0.2.10"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config masquerade ip-forward-port add eth0 192.0.2.10 TCP 8080"
    )

    port_map = rpc.config.masquerade[0].ip_forward[0].port_map[0]
    assert port_map.protocol == netfilter_pb2.TCP
    assert port_map.port == "8080"
    assert port_map.destination_port == ""
    assert rpc.updated is rpc.config


async def test_add_masquerade_port_destination_port(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "192.0.2.10"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config masquerade ip-forward-port add eth0 192.0.2.10 TCP 8080 destination-port 80"
    )

    port_map = rpc.config.masquerade[0].ip_forward[0].port_map[0]
    assert port_map.port == "8080"
    assert port_map.destination_port == "80"


async def test_remove_masquerade_port(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "192.0.2.10"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.UDP
    port_map.port = "8083"
    port_map = ip_forward.port_map.add()
    port_map.protocol = netfilter_pb2.UDP
    port_map.port = "8081"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config masquerade ip-forward-port remove eth0 192.0.2.10 UDP 8083"
    )

    assert [port_map.port for port_map in rpc.config.masquerade[0].ip_forward[0].port_map] == [
        "8081"
    ]


async def test_complete_family(cli):
    netfilter_cli = NetfilterCLI(cli, FakeRPC(netfilter_pb2.NetfilterConfig()))

    assert await netfilter_cli.complete_family() == ["IPV4", "IPV6"]


async def test_add_masquerade_forward_wrong_family(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config masquerade add eth0")

    with pytest.raises(InvalidArgument):
        await cli.handle_command(
            "netfilter config masquerade ip-forward add eth0 2001:db8::2"
        )


async def test_add_masquerade_port_unknown_destination(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command(
            "netfilter config masquerade ip-forward-port add eth0 192.0.2.10 TCP 8080"
        )


async def test_remove_masquerade_forward_missing(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command(
            "netfilter config masquerade ip-forward remove eth0 192.0.2.10"
        )


async def test_remove_masquerade_port_missing(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "192.0.2.10"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command(
            "netfilter config masquerade ip-forward-port remove eth0 192.0.2.10 TCP 8080"
        )


async def test_add_masquerade_forward_duplicate(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "192.0.2.10"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command(
            "netfilter config masquerade ip-forward add eth0 192.0.2.10"
        )


async def test_remove_masquerade_forward(cli):
    config = netfilter_pb2.NetfilterConfig()
    masquerade = config.masquerade.add()
    masquerade.interface = "eth0"
    ip_forward = masquerade.ip_forward.add()
    ip_forward.destination = "192.0.2.10"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config masquerade ip-forward remove eth0 192.0.2.10"
    )

    assert len(rpc.config.masquerade[0].ip_forward) == 0
    assert rpc.updated is rpc.config


def get_command_paths(cli):
    paths = []

    def walk(node, path):
        for name, child in node.children.items():
            walk(child, path + [name])
        if node.handler:
            paths.append(" ".join(path))

    walk(cli.router.root_node, [])
    return paths


async def test_add_duplicate(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config duplicate add 255.255.255.255 interface eth2 description lan-play"
    )

    duplicate = rpc.config.duplicate[0]
    assert duplicate.family == netfilter_pb2.IPV4
    assert duplicate.destination == "255.255.255.255"
    assert duplicate.interface == "eth2"
    assert duplicate.description == "lan-play"
    assert rpc.updated is rpc.config


async def test_add_duplicate_ipv6(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config duplicate add ff02::1 family IPV6 interface eth2"
    )

    duplicate = rpc.config.duplicate[0]
    assert duplicate.family == netfilter_pb2.IPV6
    assert duplicate.destination == "ff02::1"


async def test_add_duplicate_wrong_family(cli):
    rpc = FakeRPC(netfilter_pb2.NetfilterConfig())
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command("netfilter config duplicate add ff02::1")


async def test_remove_duplicate(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.duplicate.add().destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config duplicate remove 0")

    assert len(rpc.config.duplicate) == 0


async def test_update_duplicate(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.duplicate.add().destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config duplicate update 0 description lan-play")

    assert rpc.config.duplicate[0].description == "lan-play"
    assert rpc.config.duplicate[0].destination == "255.255.255.255"


async def test_update_duplicate_family(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.duplicate.add().destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(
        "netfilter config duplicate update 0 family IPV6 destination ff02::1"
    )

    assert rpc.config.duplicate[0].family == netfilter_pb2.IPV6
    assert rpc.config.duplicate[0].destination == "ff02::1"


async def test_update_duplicate_wrong_family(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.duplicate.add().destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    with pytest.raises(InvalidArgument):
        await cli.handle_command("netfilter config duplicate update 0 family IPV6")


@pytest.mark.parametrize(
    "match_command,match_name,field,value,stored",
    [
        ("ip-match", "ip", "source", "192.0.2.0/24", "192.0.2.0/24"),
        ("ip-match", "ip", "destination", "198.51.100.0/24", "198.51.100.0/24"),
        ("ip6-match", "ip6", "source", "2001:db8::/64", "2001:db8::/64"),
        ("tcp-match", "tcp", "destination", "22", "22"),
        ("udp-match", "udp", "destination", "5353", "5353"),
        ("icmp-match", "icmp", "code", "0", 0),
        ("icmp6-match", "icmp6", "code", "0", 0),
        ("ct-match", "ct", "state", "new", "new"),
        ("meta-match", "meta", "input-interface", "eth1", "eth1"),
    ],
)
async def test_duplicate_match_commands(
    cli, match_command, match_name, field, value, stored
):
    config = netfilter_pb2.NetfilterConfig()
    duplicate = config.duplicate.add()
    duplicate.destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)
    command = "netfilter config duplicate"

    await cli.handle_command(f"{command} {match_command} add 0 {field} {value}")
    match = getattr(rpc.config.duplicate[0], match_name)[0]
    attribute = field.replace("-", "_")
    assert list(getattr(match, attribute)) == [stored]

    await cli.handle_command(f"{command} {match_command} {field} add 0 0 {value}")
    assert list(getattr(match, attribute)) == [stored, stored]

    await cli.handle_command(f"{command} {match_command} {field} remove 0 0 {value}")
    assert list(getattr(match, attribute)) == [stored]

    await cli.handle_command(f"{command} {match_command} update 0 0 {field} {value}")
    assert list(getattr(match, attribute)) == [stored, stored]

    assert await cli.handle_command(f"{command} {match_command} list 0")

    await cli.handle_command(f"{command} {match_command} remove 0 0")
    assert len(getattr(rpc.config.duplicate[0], match_name)) == 0


async def test_duplicate_meta_output_interface(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.duplicate.add().destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command("netfilter config duplicate meta-match add 0")
    await cli.handle_command(
        "netfilter config duplicate meta-match output-interface add 0 0 eth2"
    )
    await cli.handle_command(
        "netfilter config duplicate meta-match output-interface remove 0 0 eth2"
    )

    assert list(rpc.config.duplicate[0].meta[0].output_interface) == []


async def test_duplicate_match_protocol_and_negate(cli):
    config = netfilter_pb2.NetfilterConfig()
    config.duplicate.add().destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)
    command = "netfilter config duplicate"

    await cli.handle_command(
        f"{command} ip-match add 0 destination 192.0.2.0/24 protocol udp negate true"
    )
    await cli.handle_command(f"{command} icmp-match add 0 type echo-request")
    await cli.handle_command(f"{command} meta-match add 0 protocol udp")
    await cli.handle_command(
        f"{command} ip-match update 0 0 destination 198.51.100.0/24 protocol tcp negate false"
    )
    await cli.handle_command(f"{command} icmp-match update 0 0 code 8")
    await cli.handle_command(f"{command} meta-match update 0 0 protocol tcp")

    duplicate = rpc.config.duplicate[0]
    assert list(duplicate.ip[0].destination) == ["192.0.2.0/24", "198.51.100.0/24"]
    assert list(duplicate.ip[0].protocol) == ["udp", "tcp"]
    assert duplicate.ip[0].negate is False
    assert list(duplicate.icmp[0].type) == ["echo-request"]
    assert list(duplicate.icmp[0].code) == [8]
    assert list(duplicate.meta[0].protocol) == ["udp", "tcp"]


RULE_COLLECTIONS = {
    "input": ("netfilter config input rule", "input_rule", "input"),
    "forward": ("netfilter config forward rule", "forward_rule", "forward"),
    "duplicate": ("netfilter config duplicate", "duplicate_rule", "duplicate"),
}


def get_rules_by_collection(config, collection):
    return {
        "input": config.input.rule,
        "forward": config.forward.rule,
        "duplicate": config.duplicate,
    }[collection]


@pytest.mark.parametrize("collection", RULE_COLLECTIONS)
@pytest.mark.parametrize(
    "match_command,match_name,field,value,stored",
    [
        ("ip-match", "ip", "source", "192.0.2.0/24", "192.0.2.0/24"),
        ("ip-match", "ip", "destination", "198.51.100.0/24", "198.51.100.0/24"),
        ("ip6-match", "ip6", "source", "2001:db8::/64", "2001:db8::/64"),
        ("tcp-match", "tcp", "source", "1024", "1024"),
        ("tcp-match", "tcp", "destination", "22", "22"),
        ("udp-match", "udp", "destination", "5353", "5353"),
        ("icmp-match", "icmp", "code", "0", 0),
        ("icmp6-match", "icmp6", "code", "0", 0),
        ("ct-match", "ct", "state", "new", "new"),
        ("meta-match", "meta", "input-interface", "eth1", "eth1"),
        ("meta-match", "meta", "output-interface", "eth2", "eth2"),
        ("meta-match", "meta", "protocol", "udp", "udp"),
    ],
)
async def test_match_commands(
    cli, collection, match_command, match_name, field, value, stored
):
    command, _, config_attribute = RULE_COLLECTIONS[collection]
    config = netfilter_pb2.NetfilterConfig()
    get_rules_by_collection(config, config_attribute).add()
    if config_attribute == "duplicate":
        config.duplicate[0].destination = "255.255.255.255"
    rpc = FakeRPC(config)
    NetfilterCLI(cli, rpc)

    await cli.handle_command(f"{command} {match_command} add 0")
    rules = get_rules_by_collection(rpc.config, config_attribute)
    match = getattr(rules[0], match_name)[0]
    attribute = field.replace("-", "_")

    await cli.handle_command(f"{command} {match_command} {field} add 0 0 {value}")
    assert list(getattr(match, attribute)) == [stored]

    await cli.handle_command(f"{command} {match_command} {field} remove 0 0 {value}")
    assert list(getattr(match, attribute)) == []

    await cli.handle_command(f"{command} {match_command} update 0 0 {field} {value}")
    assert list(getattr(match, attribute)) == [stored]

    assert await cli.handle_command(f"{command} {match_command} list 0")

    await cli.handle_command(f"{command} {match_command} remove 0 0")
    assert len(getattr(rules[0], match_name)) == 0
