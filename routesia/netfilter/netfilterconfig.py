"""
routesia/interface/config.py - Netfilter config
"""

import logging

from routesia.schema.v2 import netfilter_pb2

logger = logging.getLogger("netfilter")


class Zone:
    def __init__(self, config):
        self.name = config.name
        self.interfaces = []
        for interface in config.interface:
            self.interfaces.append(interface)


class Rule:
    verdict_map = {
        netfilter_pb2.Rule.Verdict.Value("ACCEPT"): "accept",
        netfilter_pb2.Rule.Verdict.Value("DROP"): "drop",
    }

    def __init__(self, config, zones):
        self.config = config
        self.zones = zones

    def get_value_set(self, field):
        values = set()
        for value in field:
            values.add(value)
        return values

    def make_rule_match(self, match_type, parameter, values, negate):
        s = ""
        if values:
            values = [str(value) for value in values]
            s += "%s %s " % (match_type, parameter)
            if negate:
                s += "!= "
            if len(values) > 1:
                s += "{"
            s += ", ".join(values)
            if len(values) > 1:
                s += "}"
            s += " "
        return s

    def __str__(self):
        s = ""

        zone_input_interfaces = set()
        for zone_name in self.config.source_zone:
            if zone_name in self.zones:
                for interface in self.zones[zone_name].interfaces:
                    zone_input_interfaces.add(interface)
        if zone_input_interfaces:
            s += self.make_rule_match("meta", "iifname", zone_input_interfaces, False)

        zone_output_interfaces = set()
        for zone_name in self.config.destination_zone:
            if zone_name in self.zones:
                for interface in self.zones[zone_name].interfaces:
                    zone_output_interfaces.add(interface)
        if zone_output_interfaces:
            s += self.make_rule_match("meta", "oifname", zone_output_interfaces, False)

        for match in self.config.ip:
            s += self.make_rule_match(
                "ip", "protocol", self.get_value_set(match.protocol), match.negate
            )
            s += self.make_rule_match(
                "ip", "saddr", self.get_value_set(match.source), match.negate
            )
            s += self.make_rule_match(
                "ip", "daddr", self.get_value_set(match.destination), match.negate
            )

        for match in self.config.ip6:
            s += self.make_rule_match(
                "ip6", "nexthdr", self.get_value_set(match.protocol), match.negate
            )
            s += self.make_rule_match(
                "ip6", "saddr", self.get_value_set(match.source), match.negate
            )
            s += self.make_rule_match(
                "ip6", "daddr", self.get_value_set(match.destination), match.negate
            )

        for match in self.config.tcp:
            s += self.make_rule_match(
                "tcp", "sport", self.get_value_set(match.source), match.negate
            )
            s += self.make_rule_match(
                "tcp", "dport", self.get_value_set(match.destination), match.negate
            )

        for match in self.config.udp:
            s += self.make_rule_match(
                "udp", "sport", self.get_value_set(match.source), match.negate
            )
            s += self.make_rule_match(
                "udp", "dport", self.get_value_set(match.destination), match.negate
            )

        for match in self.config.icmp:
            s += self.make_rule_match(
                "icmp", "type", self.get_value_set(match.type), match.negate
            )
            s += self.make_rule_match(
                "icmp", "code", self.get_value_set(match.code), match.negate
            )

        for match in self.config.icmp6:
            s += self.make_rule_match(
                "icmpv6", "type", self.get_value_set(match.type), match.negate
            )
            s += self.make_rule_match(
                "icmpv6", "code", self.get_value_set(match.code), match.negate
            )

        for match in self.config.ct:
            s += self.make_rule_match(
                "ct", "state", self.get_value_set(match.state), match.negate
            )

        for match in self.config.meta:
            s += self.make_rule_match(
                "meta",
                "iifname",
                self.get_value_set(match.input_interface),
                match.negate,
            )
            s += self.make_rule_match(
                "meta",
                "oifname",
                self.get_value_set(match.output_interface),
                match.negate,
            )
            s += self.make_rule_match(
                "meta", "protocol", self.get_value_set(match.protocol), match.negate
            )

        s += self.verdict_map[self.config.verdict]

        if self.config.description:
            s += ' comment "%s"' % self.config.description

        return s


class MasqueradeRule:
    def __init__(self, config):
        self.config = config

    def __str__(self):
        return f'meta oifname "{self.config.interface}" masquerade'


class PortForwardRule:
    def __init__(self, interface, config):
        self.interface = interface
        self.config = config

    def __str__(self):
        rules = []

        if self.config.port_map:
            udp_ports = {}
            tcp_ports = {}
            sctp_ports = {}
            for port_map in self.config.port_map:
                if port_map.protocol == netfilter_pb2.IPForwardProtocol.TCP:
                    tcp_ports[port_map.port] = port_map.destination_port if port_map.destination_port else port_map.port
                if port_map.protocol == netfilter_pb2.IPForwardProtocol.UDP:
                    udp_ports[port_map.port] = port_map.destination_port if port_map.destination_port else port_map.port
                if port_map.protocol == netfilter_pb2.IPForwardProtocol.SCTP:
                    sctp_ports[port_map.port] = port_map.destination_port if port_map.destination_port else port_map.port
            if udp_ports:
                map = ", ".join([f"{port} : {self.config.destination} . {dest_port}" for port, dest_port in udp_ports.items()])
                rules.append(f'iifname "{self.interface}" ip protocol udp dnat ip addr . port to udp dport map {{ {map} }}')
            if tcp_ports:
                map = ", ".join([f"{port} : {self.config.destination} . {dest_port}" for port, dest_port in tcp_ports.items()])
                rules.append(f'iifname "{self.interface}" ip protocol tcp dnat ip addr . port to tcp dport map {{ {map} }}')
            if sctp_ports:
                map = ", ".join([f"{port} : {self.config.destination} . {dest_port}" for port, dest_port in sctp_ports.items()])
                rules.append(f'iifname "{self.interface}" ip protocol sctp dnat ip addr . port to sctp dport map {{ {map} }}')
        else:
            rules.append(f'iifname "{self.interface}" dnat to {self.config.destination}')

        return "\n".join(rules)


class Chain:
    def __init__(self, name, chaintype, hook, priority, policy):
        self.name = name
        self.chaintype = chaintype
        self.hook = hook
        self.priority = priority
        self.policy = policy
        self.rules = []

    def __str__(self):
        s = "\tchain %s {\n" % self.name
        s += "\t\ttype %s hook %s priority %s; policy %s;\n\n" % (
            self.chaintype,
            self.hook,
            self.priority,
            self.policy,
        )

        for rule in self.rules:
            s += "\t\t%s\n" % rule

        s += "\t}\n"
        return s

    def add_rule(self, rule):
        self.rules.append(rule)


class Table:
    def __init__(self, name, tabletype):
        self.name = name
        self.tabletype = tabletype
        self.chains = {}

    def __str__(self):
        s = "table %s %s {\n" % (self.tabletype, self.name)
        for chain in self.chains.values():
            s += "%s\n" % chain
        s += "}\n"
        return s

    def add_chain(self, chain):
        self.chains[chain.name] = chain


class NetfilterConfig:
    def __init__(self, config):
        self.config = config
        self.zones = {}
        self.masquerade_interfaces = {}
        self.tables = {}
        self.load()

    def __str__(self):
        s = "flush ruleset\n\n"
        for table in self.tables.values():
            s += "%s\n" % table
        return s

    def load(self):
        for zone_config in self.config.zone:
            self.zones[zone_config.name] = Zone(zone_config)

        if self.config.masquerade:
            nat_table = Table("nat", "ip")
            self.tables[("ip", "nat")] = nat_table

            prerouting = Chain("prerouting", "nat", "prerouting", 0, "accept")
            nat_table.add_chain(prerouting)
            postrouting = Chain("postrouting", "nat", "postrouting", 100, "accept")
            nat_table.add_chain(postrouting)

            for masquerade in self.config.masquerade:
                postrouting.add_rule(MasqueradeRule(masquerade))

                for ip_forward in masquerade.ip_forward:
                    prerouting.add_rule(PortForwardRule(masquerade.interface, ip_forward))

        filter_table = Table("filter", "inet")

        input_policy = (
            "drop" if self.config.input.policy == netfilter_pb2.DROP else "accept"
        )
        input_chain = Chain("input", "filter", "input", 0, input_policy)
        for rule_config in self.config.input.rule:
            input_chain.add_rule(Rule(rule_config, self.zones))
        filter_table.add_chain(input_chain)

        forward_policy = (
            "drop" if self.config.forward.policy == netfilter_pb2.DROP else "accept"
        )
        forward_chain = Chain("forward", "filter", "forward", 0, forward_policy)
        for rule_config in self.config.forward.rule:
            forward_chain.add_rule(Rule(rule_config, self.zones))
        filter_table.add_chain(forward_chain)

        self.tables[("inet", "filter")] = filter_table
