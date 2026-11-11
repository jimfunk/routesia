"""
routesia/interface/config.py - Netfilter config
"""

import logging

from routesia.schema.v1 import interface_pb2, netfilter_pb2

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

        s += self.make_matches()
        s += self.verdict_map[self.config.verdict]

        if self.config.description:
            s += ' comment "%s"' % self.config.description

        return s


    def make_matches(self):
        s = ""

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

        return s


class MasqueradeRule:
    def __init__(self, config):
        self.config = config

    def __str__(self):
        return f'meta oifname "{self.config.interface}" masquerade'


class PortForwardRule:
    def __init__(self, interface, family, config):
        self.interface = interface
        self.family = family
        self.config = config
        if family == "ip6":
            self.protocol_match = "ip6 nexthdr"
            self.dnat = "dnat ip6 addr . port"
            self.dnat_to = "dnat ip6 to"
        else:
            self.protocol_match = "ip protocol"
            self.dnat = "dnat ip addr . port"
            self.dnat_to = "dnat to"

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
                rules.append(f'iifname "{self.interface}" {self.protocol_match} udp {self.dnat} to udp dport map {{ {map} }}')
            if tcp_ports:
                map = ", ".join([f"{port} : {self.config.destination} . {dest_port}" for port, dest_port in tcp_ports.items()])
                rules.append(f'iifname "{self.interface}" {self.protocol_match} tcp {self.dnat} to tcp dport map {{ {map} }}')
            if sctp_ports:
                map = ", ".join([f"{port} : {self.config.destination} . {dest_port}" for port, dest_port in sctp_ports.items()])
                rules.append(f'iifname "{self.interface}" {self.protocol_match} sctp {self.dnat} to sctp dport map {{ {map} }}')
        else:
            rules.append(f'iifname "{self.interface}" {self.dnat_to} {self.config.destination}')

        return "\n".join(rules)


class MSSClampRule:
    def __init__(self, interface, mss):
        self.interface = interface
        self.mss = mss

    def __str__(self):
        return (
            f'meta oifname "{self.interface}" tcp flags syn '
            f"tcp option maxseg size set {self.mss}"
        )


class DuplicateRule(Rule):
    def __init__(self, config):
        super().__init__(config, {})

    def __str__(self):
        s = self.make_matches()
        s += "dup to %s" % self.config.destination
        if self.config.interface:
            s += ' device "%s"' % self.config.interface
        if self.config.description:
            s += ' comment "%s"' % self.config.description
        return s


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
    def __init__(self, config, interfaces=None):
        self.config = config
        self.interfaces = interfaces
        self.zones = {}
        self.masquerade_interfaces = {}
        self.tables = {}
        self.load()

    def __str__(self):
        s = "flush ruleset\n\n"
        for table in self.tables.values():
            s += "%s\n" % table
        return s

    def has_content(self):
        return bool(self.tables)

    def load(self):
        for zone_config in self.config.zone:
            self.zones[zone_config.name] = Zone(zone_config)

        for masquerade in self.config.masquerade:
            if masquerade.family == netfilter_pb2.IPV6:
                family = "ip6"
            else:
                family = "ip"

            if (family, "nat") not in self.tables:
                nat_table = Table("nat", family)
                self.tables[(family, "nat")] = nat_table
                nat_table.add_chain(
                    Chain("prerouting", "nat", "prerouting", 0, "accept")
                )
                nat_table.add_chain(
                    Chain("postrouting", "nat", "postrouting", 100, "accept")
                )

            nat_table = self.tables[(family, "nat")]
            nat_table.chains["postrouting"].add_rule(MasqueradeRule(masquerade))

            for ip_forward in masquerade.ip_forward:
                nat_table.chains["prerouting"].add_rule(
                    PortForwardRule(masquerade.interface, family, ip_forward)
                )

        input_policy = (
            "drop" if self.config.input.policy == netfilter_pb2.DROP else "accept"
        )
        forward_policy = (
            "drop" if self.config.forward.policy == netfilter_pb2.DROP else "accept"
        )

        if (
            self.config.input.rule
            or self.config.forward.rule
            or input_policy == "drop"
            or forward_policy == "drop"
        ):
            filter_table = Table("filter", "inet")

            input_chain = Chain("input", "filter", "input", 0, input_policy)
            for rule_config in self.config.input.rule:
                input_chain.add_rule(Rule(rule_config, self.zones))
            filter_table.add_chain(input_chain)

            forward_chain = Chain("forward", "filter", "forward", 0, forward_policy)
            for rule_config in self.config.forward.rule:
                forward_chain.add_rule(Rule(rule_config, self.zones))
            filter_table.add_chain(forward_chain)

            self.tables[("inet", "filter")] = filter_table

        for family in ("ip", "ip6"):
            duplicates = []
            for duplicate_config in self.config.duplicate:
                if (duplicate_config.family == netfilter_pb2.IPV6) == (family == "ip6"):
                    duplicates.append(duplicate_config)

            mss_clamps = self.get_mss_clamps(family)

            if not duplicates and not mss_clamps:
                continue

            mangle_table = Table("mangle", family)
            self.tables[(family, "mangle")] = mangle_table

            if duplicates:
                prerouting = Chain("prerouting", "filter", "prerouting", "mangle", "accept")
                mangle_table.add_chain(prerouting)
                for duplicate_config in duplicates:
                    prerouting.add_rule(DuplicateRule(duplicate_config))

            if mss_clamps:
                postrouting = Chain("postrouting", "filter", "postrouting", 0, "accept")
                mangle_table.add_chain(postrouting)
                for interface, mss in mss_clamps:
                    postrouting.add_rule(MSSClampRule(interface, mss))

    def get_mss_clamps(self, family):
        clamps = []
        if self.interfaces is None:
            return clamps
        if family == "ip6":
            offset = 60
        else:
            offset = 40

        for interface in self.interfaces.interface:
            clamp = interface.mss_clamp
            if not clamp.mtu:
                continue
            if clamp.family == interface_pb2.MSSClamp.IPV4 and family != "ip":
                continue
            if clamp.family == interface_pb2.MSSClamp.IPV6 and family != "ip6":
                continue
            clamps.append((interface.name, clamp.mtu - offset))
        return clamps
