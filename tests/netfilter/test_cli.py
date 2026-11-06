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
