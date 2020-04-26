"""
routesia/netfilter/commands.py - Routesia netfilter commands
"""

import textwrap
from prompt_toolkit.completion import Completion

from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import (
    String,
    IPAddress,
    IPNetwork,
    UInt16,
    UInt32,
    Bool,
    List,
    ProtobufEnum,
)
from routesia.exceptions import CommandError
from routesia.interface import interface_pb2
from routesia.netfilter import netfilter_pb2


class ConfigShow(CLICommand):
    command = "netfilter config show"

    async def call(self, name=None) -> netfilter_pb2.NetfilterConfig:
        return netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )


class ConfigZoneAdd(CLICommand):
    command = "netfilter config zone add"
    parameters = (("name", String(required=True)),)

    async def call(self, name, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )

        for zone in config.zone:
            if zone.name == name:
                raise CommandError("Zone already exists")

        zone = config.zone.add()
        zone.name = name
        await self.client.request("/netfilter/config/update", config)


async def get_zone_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    for zone in config.zone:
        completions.append(zone.name)
    return completions


class ConfigZoneRemove(CLICommand):
    command = "netfilter config zone remove"
    parameters = (("name", String(required=True, completer=get_zone_completions),),)

    async def call(self, name, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        for i, zone in enumerate(config.zone):
            if zone.name == name:
                del config.zone[i]
                break
        await self.client.request("/netfilter/config/update", config)


class ZoneCLICommand(CLICommand):
    def get_zone(self, config, name):
        for zone in config.zone:
            if zone.name == name:
                return zone
        raise CommandError("Zone %s does not exist" % name)


class InterfaceParameter(String):
    def __init__(self, **kwargs):
        super().__init__(max_length=15, **kwargs)

    async def get_completions(self, client, suggestion, **kwargs):
        if self.completer:
            return await self.completer(client, suggestion, **kwargs)
        completions = set()
        data = await client.request("/interface/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.add(interface.name)
        data = await client.request("/interface/config/list", None)
        interface_list = interface_pb2.InterfaceList.FromString(data)
        for interface in interface_list.interface:
            if interface.name.startswith(suggestion):
                completions.add(interface.name)
        return list(completions)


class ConfigZoneInterfaceAdd(ZoneCLICommand):
    command = "netfilter config zone interface add"
    parameters = (
        ("zone", String(required=True, completer=get_zone_completions)),
        ("interface", InterfaceParameter(required=True)),
    )

    async def call(self, zone, interface, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        zone = self.get_zone(config, zone)
        for zone_interface in zone.interface:
            if zone_interface == interface:
                raise CommandError(
                    "Interface %s already exists in zone %s" % (interface, zone.name)
                )
        zone.interface.append(interface)
        await self.client.request("/netfilter/config/update", config)


async def get_zone_interface_completions(client, suggestion, **kwargs):
    completions = []
    if "zone" not in kwargs:
        return completions
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for interface in zone.interface:
        completions.append(interface)
    return completions


class ConfigZoneInterfaceRemove(ZoneCLICommand):
    command = "netfilter config zone interface remove"
    parameters = (
        ("zone", String(required=True, completer=get_zone_completions)),
        (
            "interface",
            InterfaceParameter(required=True, completer=get_zone_interface_completions),
        ),
    )

    async def call(self, zone, interface, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        zone = self.get_zone(config, zone)
        for i, zone_interface in enumerate(zone.interface):
            if zone_interface == interface:
                del zone.interface[i]
                break
        await self.client.request("/netfilter/config/update", config)


class ConfigMasqueradeAdd(CLICommand):
    command = "netfilter config masquerade add"
    parameters = (("interface", InterfaceParameter(required=True)),)

    async def call(self, interface, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                raise CommandError("Masqeurade already exists")

        masquerade = config.masquerade.add()
        masquerade.interface = interface
        await self.client.request("/netfilter/config/update", config)


async def get_masquerade_interface_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    for masquerade in config.masquerade:
        completions.append(masquerade.interface)
    return completions


class ConfigMasqueradeRemove(CLICommand):
    command = "netfilter config masquerade remove"
    parameters = (
        (
            "interface",
            InterfaceParameter(
                required=True, completer=get_masquerade_interface_completions
            ),
        ),
    )

    async def call(self, interface, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        for i, masquerade in enumerate(config.masquerade):
            if masquerade.interface == interface:
                del config.masquerade[i]
                break
        await self.client.request("/netfilter/config/update", config)


class ConfigInputPolicy(CLICommand):
    command = "netfilter config input policy"
    parameters = (("policy", ProtobufEnum(netfilter_pb2.Policy, required=True)),)

    async def call(self, policy, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        config.input.policy = policy
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleList(CLICommand):
    command = "netfilter config input rule list"

    async def call(self, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        for i, rule in enumerate(config.input.rule):
            print("%s:" % i)
            print(textwrap.indent(str(rule), "    "))


class ConfigInputRuleAdd(CLICommand):
    command = "netfilter config input rule add"
    parameters = (
        ("description", String()),
        (
            "verdict",
            ProtobufEnum(netfilter_pb2.Rule.Verdict, valid_values=("ACCEPT", "DROP")),
        ),
    )

    async def call(self, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule.add()
        self.update_message_from_args(rule, **kwargs)
        await self.client.request("/netfilter/config/update", config)


async def get_input_rule_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    for order, rule in enumerate(config.input.rule):
        completions.append(Completion(str(order), display="%s %s" % (order, rule.description)))
    return completions


class ConfigInputRuleUpdate(CLICommand):
    command = "netfilter config input rule update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("description", String()),
        (
            "verdict",
            ProtobufEnum(netfilter_pb2.Rule.Verdict, valid_values=("ACCEPT", "DROP")),
        ),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        self.update_message_from_args(rule, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleRemove(CLICommand):
    command = "netfilter config input rule remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        del config.input.rule[rule]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleZoneAdd(CLICommand):
    command = "netfilter config input rule zone add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("zone", String(required=True, completer=get_zone_completions)),
    )

    async def call(self, rule, zone, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for zone_config in config.zone:
            if zone_config.name == zone:
                break
        else:
            raise CommandError("Zone %s does not exist" % zone)
        for rule_zone in rule.source_zone:
            if rule_zone == zone:
                raise CommandError("Zone %s is already set on rule" % zone)
        rule.source_zone.append(zone)
        await self.client.request("/netfilter/config/update", config)


async def get_input_rule_zone_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for zone in rule.source_zone:
        completions.append(zone)
    return completions


class ConfigInputRuleZoneRemove(CLICommand):
    command = "netfilter config input rule zone remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("zone", String(required=True, completer=get_input_rule_zone_completions)),
    )

    async def call(self, rule, zone, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, zone_name in enumerate(rule.source_zone):
            if zone_name == zone:
                del rule.source_zone[i]
                break
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleIPMatchAdd(CLICommand):
    command = "netfilter config input rule ip-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("source", List(IPNetwork(version=4))),
        ("destination", List(IPNetwork(version=4))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.ip.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleIPMatchList(CLICommand):
    command = "netfilter config input rule ip-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.ip):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_ip_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.ip):
        desc = ""
        if match.negate:
            desc += "! "
        if match.protocol:
            desc += "protocol=%s " % ",".join(match.protocol)
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleIPMatchUpdate(CLICommand):
    command = "netfilter config input rule ip-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_ip_match_completions)),
        ("source", List(IPNetwork(version=4))),
        ("destination", List(IPNetwork(version=4))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.ip[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleIPMatchRemove(CLICommand):
    command = "netfilter config input rule ip-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_ip_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.ip[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleIP6MatchAdd(CLICommand):
    command = "netfilter config input rule ip6-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("source", List(IPNetwork(version=6))),
        ("destination", List(IPNetwork(version=6))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.ip6.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleIP6MatchList(CLICommand):
    command = "netfilter config input rule ip6-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.ip6):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_ip6_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.ip6):
        desc = ""
        if match.negate:
            desc += "! "
        if match.protocol:
            desc += "protocol=%s " % ",".join(match.protocol)
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleIP6MatchUpdate(CLICommand):
    command = "netfilter config input rule ip6-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_ip6_match_completions)),
        ("source", List(IPNetwork(version=6))),
        ("destination", List(IPNetwork(version=6))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.ip6[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleIP6MatchRemove(CLICommand):
    command = "netfilter config input rule ip6-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_ip6_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.ip6[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleTCPMatchAdd(CLICommand):
    command = "netfilter config input rule tcp-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.tcp.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleTCPMatchList(CLICommand):
    command = "netfilter config input rule tcp-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.tcp):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_tcp_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.tcp):
        desc = ""
        if match.negate:
            desc += "! "
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleTCPMatchUpdate(CLICommand):
    command = "netfilter config input rule tcp-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_tcp_match_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.tcp[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleTCPMatchRemove(CLICommand):
    command = "netfilter config input rule tcp-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_tcp_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.tcp[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleUDPMatchAdd(CLICommand):
    command = "netfilter config input rule udp-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.udp.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleUDPMatchList(CLICommand):
    command = "netfilter config input rule udp-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.udp):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_udp_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.udp):
        desc = ""
        if match.negate:
            desc += "! "
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleUDPMatchUpdate(CLICommand):
    command = "netfilter config input rule udp-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_udp_match_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.udp[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleUDPMatchRemove(CLICommand):
    command = "netfilter config input rule udp-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_udp_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.udp[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleICMPMatchAdd(CLICommand):
    command = "netfilter config input rule icmp-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.icmp.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleICMPMatchList(CLICommand):
    command = "netfilter config input rule icmp-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.icmp):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_icmp_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.icmp):
        desc = ""
        if match.negate:
            desc += "! "
        if match.type:
            desc += "type=%s " % ",".join(match.type)
        if match.code:
            desc += "code=%s " % ",".join(match.code)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleICMPMatchUpdate(CLICommand):
    command = "netfilter config input rule icmp-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_icmp_match_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.icmp[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleICMPMatchRemove(CLICommand):
    command = "netfilter config input rule icmp-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_icmp_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.icmp[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleICMP6MatchAdd(CLICommand):
    command = "netfilter config input rule icmp6-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.icmp6.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleICMP6MatchList(CLICommand):
    command = "netfilter config input rule icmp6-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.icmp6):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_icmp6_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.icmp6):
        desc = ""
        if match.negate:
            desc += "! "
        if match.type:
            desc += "type=%s " % ",".join(match.type)
        if match.code:
            desc += "code=%s " % ",".join(match.code)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleICMP6MatchUpdate(CLICommand):
    command = "netfilter config input rule icmp6-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_icmp6_match_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.icmp6[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleICMP6MatchRemove(CLICommand):
    command = "netfilter config input rule icmp6-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_icmp6_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.icmp6[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleCTMatchAdd(CLICommand):
    command = "netfilter config input rule ct-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("state", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.ct.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleCTMatchList(CLICommand):
    command = "netfilter config input rule ct-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.ct):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_ct_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.ct):
        desc = ""
        if match.negate:
            desc += "! "
        if match.state:
            desc += "state=%s " % ",".join(match.state)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleCTMatchUpdate(CLICommand):
    command = "netfilter config input rule ct-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_ct_match_completions)),
        ("state", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.ct[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleCTMatchRemove(CLICommand):
    command = "netfilter config input rule ct-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_ct_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.ct[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleMetaMatchAdd(CLICommand):
    command = "netfilter config input rule meta-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("input-interface", List(String())),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.meta.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleMetaMatchList(CLICommand):
    command = "netfilter config input rule meta-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        for i, match in enumerate(rule.meta):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_input_rule_meta_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.input.rule):
        return completions
    rule = config.input.rule[kwargs["rule"]]
    for order, match in enumerate(rule.meta):
        desc = ""
        if match.negate:
            desc += "! "
        if match.input_interface:
            desc += "input-interface=%s " % ",".join(match.input_interface)
        if match.protocol:
            desc += "protocol=%s " % ",".join(match.protocol)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigInputRuleMetaMatchUpdate(CLICommand):
    command = "netfilter config input rule meta-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_meta_match_completions)),
        ("input-interface", List(String())),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        match = rule.meta[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigInputRuleMetaMatchRemove(CLICommand):
    command = "netfilter config input rule meta-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_input_rule_completions)),
        ("match", UInt32(required=True, completer=get_input_rule_meta_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.input.rule[rule]
        del rule.meta[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardPolicy(CLICommand):
    command = "netfilter config forward policy"
    parameters = (("policy", ProtobufEnum(netfilter_pb2.Policy, required=True)),)

    async def call(self, policy, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        config.forward.policy = policy
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleList(CLICommand):
    command = "netfilter config forward rule list"

    async def call(self, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        for i, rule in enumerate(config.forward.rule):
            print("%s:" % i)
            print(textwrap.indent(str(rule), "    "))


class ConfigForwardRuleAdd(CLICommand):
    command = "netfilter config forward rule add"
    parameters = (
        ("description", String()),
        (
            "verdict",
            ProtobufEnum(netfilter_pb2.Rule.Verdict, valid_values=("ACCEPT", "DROP")),
        ),
    )

    async def call(self, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule.add()
        self.update_message_from_args(rule, **kwargs)
        await self.client.request("/netfilter/config/update", config)


async def get_forward_rule_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    for order, rule in enumerate(config.forward.rule):
        completions.append(Completion(str(order), display="%s %s" % (order, rule.description)))
    return completions


class ConfigForwardRuleUpdate(CLICommand):
    command = "netfilter config forward rule update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("description", String()),
        (
            "verdict",
            ProtobufEnum(netfilter_pb2.Rule.Verdict, valid_values=("ACCEPT", "DROP")),
        ),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        self.update_message_from_args(rule, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleRemove(CLICommand):
    command = "netfilter config forward rule remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        del config.forward.rule[rule]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleSourceZoneAdd(CLICommand):
    command = "netfilter config forward rule source-zone add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("zone", String(required=True, completer=get_zone_completions)),
    )

    async def call(self, rule, zone, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for zone_config in config.zone:
            if zone_config.name == zone:
                break
        else:
            raise CommandError("Zone %s does not exist" % zone)
        for rule_zone in rule.source_zone:
            if rule_zone == zone:
                raise CommandError("Zone %s is already set on rule" % zone)
        rule.source_zone.append(zone)
        await self.client.request("/netfilter/config/update", config)


async def get_forward_rule_zone_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for zone in rule.source_zone:
        completions.append(zone)
    return completions


class ConfigForwardRuleSourceZoneRemove(CLICommand):
    command = "netfilter config forward rule source-zone remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("zone", String(required=True, completer=get_forward_rule_zone_completions)),
    )

    async def call(self, rule, zone, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, zone_name in enumerate(rule.source_zone):
            if zone_name == zone:
                del rule.source_zone[i]
                break
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleDestinationZoneAdd(CLICommand):
    command = "netfilter config forward rule destination-zone add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("zone", String(required=True, completer=get_zone_completions)),
    )

    async def call(self, rule, zone, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for zone_config in config.zone:
            if zone_config.name == zone:
                break
        else:
            raise CommandError("Zone %s does not exist" % zone)
        for rule_zone in rule.destination_zone:
            if rule_zone == zone:
                raise CommandError("Zone %s is already set on rule" % zone)
        rule.destination_zone.append(zone)
        await self.client.request("/netfilter/config/update", config)


async def get_forward_rule_zone_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for zone in rule.destination_zone:
        completions.append(zone)
    return completions


class ConfigForwardRuleDestinationZoneRemove(CLICommand):
    command = "netfilter config forward rule destination-zone remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("zone", String(required=True, completer=get_forward_rule_zone_completions)),
    )

    async def call(self, rule, zone, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, zone_name in enumerate(rule.destination_zone):
            if zone_name == zone:
                del rule.destination_zone[i]
                break
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleIPMatchAdd(CLICommand):
    command = "netfilter config forward rule ip-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("source", List(IPNetwork(version=4))),
        ("destination", List(IPNetwork(version=4))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.ip.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleIPMatchList(CLICommand):
    command = "netfilter config forward rule ip-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.ip):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_ip_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.ip):
        desc = ""
        if match.negate:
            desc += "! "
        if match.protocol:
            desc += "protocol=%s " % ",".join(match.protocol)
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleIPMatchUpdate(CLICommand):
    command = "netfilter config forward rule ip-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_ip_match_completions)),
        ("source", List(IPNetwork(version=4))),
        ("destination", List(IPNetwork(version=4))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.ip[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleIPMatchRemove(CLICommand):
    command = "netfilter config forward rule ip-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_ip_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.ip[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleIP6MatchAdd(CLICommand):
    command = "netfilter config forward rule ip6-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("source", List(IPNetwork(version=6))),
        ("destination", List(IPNetwork(version=6))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.ip6.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleIP6MatchList(CLICommand):
    command = "netfilter config forward rule ip6-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.ip6):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_ip6_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.ip6):
        desc = ""
        if match.negate:
            desc += "! "
        if match.protocol:
            desc += "protocol=%s " % ",".join(match.protocol)
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleIP6MatchUpdate(CLICommand):
    command = "netfilter config forward rule ip6-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_ip6_match_completions)),
        ("source", List(IPNetwork(version=6))),
        ("destination", List(IPNetwork(version=6))),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.ip6[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleIP6MatchRemove(CLICommand):
    command = "netfilter config forward rule ip6-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_ip6_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.ip6[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleTCPMatchAdd(CLICommand):
    command = "netfilter config forward rule tcp-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.tcp.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleTCPMatchList(CLICommand):
    command = "netfilter config forward rule tcp-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.tcp):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_tcp_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.tcp):
        desc = ""
        if match.negate:
            desc += "! "
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleTCPMatchUpdate(CLICommand):
    command = "netfilter config forward rule tcp-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_tcp_match_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.tcp[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleTCPMatchRemove(CLICommand):
    command = "netfilter config forward rule tcp-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_tcp_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.tcp[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleUDPMatchAdd(CLICommand):
    command = "netfilter config forward rule udp-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.udp.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleUDPMatchList(CLICommand):
    command = "netfilter config forward rule udp-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.udp):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_udp_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.udp):
        desc = ""
        if match.negate:
            desc += "! "
        if match.source:
            desc += "source=%s " % ",".join(match.source)
        if match.destination:
            desc += "destination=%s " % ",".join(match.destination)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleUDPMatchUpdate(CLICommand):
    command = "netfilter config forward rule udp-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_udp_match_completions)),
        ("source", List(String())),
        ("destination", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.udp[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleUDPMatchRemove(CLICommand):
    command = "netfilter config forward rule udp-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_udp_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.udp[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleICMPMatchAdd(CLICommand):
    command = "netfilter config forward rule icmp-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.icmp.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleICMPMatchList(CLICommand):
    command = "netfilter config forward rule icmp-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.icmp):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_icmp_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.icmp):
        desc = ""
        if match.negate:
            desc += "! "
        if match.type:
            desc += "type=%s " % ",".join(match.type)
        if match.code:
            desc += "code=%s " % ",".join(match.code)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleICMPMatchUpdate(CLICommand):
    command = "netfilter config forward rule icmp-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_icmp_match_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.icmp[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleICMPMatchRemove(CLICommand):
    command = "netfilter config forward rule icmp-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_icmp_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.icmp[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleICMP6MatchAdd(CLICommand):
    command = "netfilter config forward rule icmp6-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.icmp6.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleICMP6MatchList(CLICommand):
    command = "netfilter config forward rule icmp6-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.icmp6):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_icmp6_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.icmp6):
        desc = ""
        if match.negate:
            desc += "! "
        if match.type:
            desc += "type=%s " % ",".join(match.type)
        if match.code:
            desc += "code=%s " % ",".join(match.code)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleICMP6MatchUpdate(CLICommand):
    command = "netfilter config forward rule icmp6-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_icmp6_match_completions)),
        ("type", List(String())),
        ("code", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.icmp6[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleICMP6MatchRemove(CLICommand):
    command = "netfilter config forward rule icmp6-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_icmp6_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.icmp6[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleCTMatchAdd(CLICommand):
    command = "netfilter config forward rule ct-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("state", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.ct.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleCTMatchList(CLICommand):
    command = "netfilter config forward rule ct-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.ct):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_ct_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.ct):
        desc = ""
        if match.negate:
            desc += "! "
        if match.state:
            desc += "state=%s " % ",".join(match.state)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleCTMatchUpdate(CLICommand):
    command = "netfilter config forward rule ct-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_ct_match_completions)),
        ("state", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.ct[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleCTMatchRemove(CLICommand):
    command = "netfilter config forward rule ct-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_ct_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.ct[match]
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleMetaMatchAdd(CLICommand):
    command = "netfilter config forward rule meta-match add"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("input-interface", List(String())),
        ("output-interface", List(String())),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.meta.add()
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleMetaMatchList(CLICommand):
    command = "netfilter config forward rule meta-match list"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
    )

    async def call(self, rule, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        for i, match in enumerate(rule.meta):
            print("%s:" % i)
            print(textwrap.indent(str(match), "    "))


async def get_forward_rule_meta_match_completions(client, suggestion, **kwargs):
    completions = []
    config = netfilter_pb2.NetfilterConfig.FromString(
        await client.request("/netfilter/config/get", None)
    )
    if "rule" not in kwargs or kwargs["rule"] >= len(config.forward.rule):
        return completions
    rule = config.forward.rule[kwargs["rule"]]
    for order, match in enumerate(rule.meta):
        desc = ""
        if match.negate:
            desc += "! "
        if match.input_interface:
            desc += "input-interface=%s " % ",".join(match.input_interface)
        if match.output_interface:
            desc += "output-interface=%s " % ",".join(match.output_interface)
        if match.protocol:
            desc += "protocol=%s " % ",".join(match.protocol)
        completions.append(Completion(str(order), display="%s %s" % (order, desc)))
    return completions


class ConfigForwardRuleMetaMatchUpdate(CLICommand):
    command = "netfilter config forward rule meta-match update"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_meta_match_completions)),
        ("input-interface", List(String())),
        ("output-interface", List(String())),
        ("protocol", List(String())),
        ("negate", Bool()),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        match = rule.meta[match]
        self.update_message_from_args(match, **kwargs)
        await self.client.request("/netfilter/config/update", config)


class ConfigForwardRuleMetaMatchRemove(CLICommand):
    command = "netfilter config forward rule meta-match remove"
    parameters = (
        ("rule", UInt32(required=True, completer=get_forward_rule_completions)),
        ("match", UInt32(required=True, completer=get_forward_rule_meta_match_completions)),
    )

    async def call(self, rule, match, **kwargs):
        config = netfilter_pb2.NetfilterConfig.FromString(
            await self.client.request("/netfilter/config/get", None)
        )
        rule = config.forward.rule[rule]
        del rule.meta[match]
        await self.client.request("/netfilter/config/update", config)


class NetfilterCommandSet(CLICommandSet):
    commands = (
        ConfigShow,
        ConfigZoneAdd,
        ConfigZoneRemove,
        ConfigZoneInterfaceAdd,
        ConfigZoneInterfaceRemove,
        ConfigMasqueradeAdd,
        ConfigMasqueradeRemove,
        ConfigInputPolicy,
        ConfigInputRuleList,
        ConfigInputRuleAdd,
        ConfigInputRuleUpdate,
        ConfigInputRuleRemove,
        ConfigInputRuleZoneAdd,
        ConfigInputRuleZoneRemove,
        ConfigInputRuleIPMatchAdd,
        ConfigInputRuleIPMatchList,
        ConfigInputRuleIPMatchUpdate,
        ConfigInputRuleIPMatchRemove,
        ConfigInputRuleIP6MatchAdd,
        ConfigInputRuleIP6MatchList,
        ConfigInputRuleIP6MatchUpdate,
        ConfigInputRuleIP6MatchRemove,
        ConfigInputRuleTCPMatchAdd,
        ConfigInputRuleTCPMatchList,
        ConfigInputRuleTCPMatchUpdate,
        ConfigInputRuleTCPMatchRemove,
        ConfigInputRuleUDPMatchAdd,
        ConfigInputRuleUDPMatchList,
        ConfigInputRuleUDPMatchUpdate,
        ConfigInputRuleUDPMatchRemove,
        ConfigInputRuleICMPMatchAdd,
        ConfigInputRuleICMPMatchList,
        ConfigInputRuleICMPMatchUpdate,
        ConfigInputRuleICMPMatchRemove,
        ConfigInputRuleICMP6MatchAdd,
        ConfigInputRuleICMP6MatchList,
        ConfigInputRuleICMP6MatchUpdate,
        ConfigInputRuleICMP6MatchRemove,
        ConfigInputRuleCTMatchAdd,
        ConfigInputRuleCTMatchList,
        ConfigInputRuleCTMatchUpdate,
        ConfigInputRuleCTMatchRemove,
        ConfigInputRuleMetaMatchAdd,
        ConfigInputRuleMetaMatchList,
        ConfigInputRuleMetaMatchUpdate,
        ConfigInputRuleMetaMatchRemove,
        ConfigForwardPolicy,
        ConfigForwardRuleList,
        ConfigForwardRuleAdd,
        ConfigForwardRuleUpdate,
        ConfigForwardRuleRemove,
        ConfigForwardRuleSourceZoneAdd,
        ConfigForwardRuleSourceZoneRemove,
        ConfigForwardRuleDestinationZoneAdd,
        ConfigForwardRuleDestinationZoneRemove,
        ConfigForwardRuleIPMatchAdd,
        ConfigForwardRuleIPMatchList,
        ConfigForwardRuleIPMatchUpdate,
        ConfigForwardRuleIPMatchRemove,
        ConfigForwardRuleIP6MatchAdd,
        ConfigForwardRuleIP6MatchList,
        ConfigForwardRuleIP6MatchUpdate,
        ConfigForwardRuleIP6MatchRemove,
        ConfigForwardRuleTCPMatchAdd,
        ConfigForwardRuleTCPMatchList,
        ConfigForwardRuleTCPMatchUpdate,
        ConfigForwardRuleTCPMatchRemove,
        ConfigForwardRuleUDPMatchAdd,
        ConfigForwardRuleUDPMatchList,
        ConfigForwardRuleUDPMatchUpdate,
        ConfigForwardRuleUDPMatchRemove,
        ConfigForwardRuleICMPMatchAdd,
        ConfigForwardRuleICMPMatchList,
        ConfigForwardRuleICMPMatchUpdate,
        ConfigForwardRuleICMPMatchRemove,
        ConfigForwardRuleICMP6MatchAdd,
        ConfigForwardRuleICMP6MatchList,
        ConfigForwardRuleICMP6MatchUpdate,
        ConfigForwardRuleICMP6MatchRemove,
        ConfigForwardRuleCTMatchAdd,
        ConfigForwardRuleCTMatchList,
        ConfigForwardRuleCTMatchUpdate,
        ConfigForwardRuleCTMatchRemove,
        ConfigForwardRuleMetaMatchAdd,
        ConfigForwardRuleMetaMatchList,
        ConfigForwardRuleMetaMatchUpdate,
        ConfigForwardRuleMetaMatchRemove,
    )
