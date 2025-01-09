"""
routesia/netfilter/cli.py - Routesia netfilter commands
"""

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
import textwrap

from routesia.cli.completion import Completion
from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import UInt16, UInt32
from routesia.rpcclient import RPCClient
from routesia.schema.v2 import netfilter_pb2
from routesia.service import Provider


class NetfilterCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("netfilter")
        self.rpc = rpc

        self.cli.add_argument_completer("protocol", self.complete_protocol)
        self.cli.add_argument_completer("zone", self.complete_zone)
        self.cli.add_argument_completer("zone-interface", self.complete_zone_interface)
        self.cli.add_argument_completer(
            "masquerade-interface", self.complete_masquerade_interface
        )
        self.cli.add_argument_completer(
            "masquerade-destination", self.complete_masquerade_destination
        )
        self.cli.add_argument_completer(
            "masquerade-port", self.complete_masquerade_port
        )
        self.cli.add_argument_completer("policy", self.complete_policy)
        self.cli.add_argument_completer("verdict", self.complete_verdict)
        self.cli.add_argument_completer("input-rule", self.complete_input_rule)
        self.cli.add_argument_completer(
            "input-rule-zone", self.complete_input_rule_zone
        )
        self.cli.add_argument_completer(
            "input-rule-ip-match", self.complete_input_rule_ip_match
        )
        self.cli.add_argument_completer(
            "input-rule-ip6-match", self.complete_input_rule_ip6_match
        )
        self.cli.add_argument_completer(
            "input-rule-tcp-match", self.complete_input_rule_tcp_match
        )
        self.cli.add_argument_completer(
            "input-rule-udp-match", self.complete_input_rule_udp_match
        )
        self.cli.add_argument_completer(
            "input-rule-icmp-match", self.complete_input_rule_icmp_match
        )
        self.cli.add_argument_completer(
            "input-rule-icmp6-match", self.complete_input_rule_icmp6_match
        )
        self.cli.add_argument_completer(
            "input-rule-ct-match", self.complete_input_rule_ct_match
        )
        self.cli.add_argument_completer(
            "input-rule-meta-match", self.complete_input_rule_meta_match
        )
        self.cli.add_argument_completer("forward-rule", self.complete_forward_rule)
        self.cli.add_argument_completer(
            "forward-rule-zone", self.complete_forward_rule_zone
        )
        self.cli.add_argument_completer(
            "forward-rule-ip-match", self.complete_forward_rule_ip_match
        )
        self.cli.add_argument_completer(
            "forward-rule-ip6-match", self.complete_forward_rule_ip6_match
        )
        self.cli.add_argument_completer(
            "forward-rule-tcp-match", self.complete_forward_rule_tcp_match
        )
        self.cli.add_argument_completer(
            "forward-rule-udp-match", self.complete_forward_rule_udp_match
        )
        self.cli.add_argument_completer(
            "forward-rule-icmp-match", self.complete_forward_rule_icmp_match
        )
        self.cli.add_argument_completer(
            "forward-rule-icmp6-match", self.complete_forward_rule_icmp6_match
        )
        self.cli.add_argument_completer(
            "forward-rule-ct-match", self.complete_forward_rule_ct_match
        )
        self.cli.add_argument_completer(
            "forward-rule-meta-match", self.complete_forward_rule_meta_match
        )

        self.cli.add_command("netfilter config show", self.show)
        self.cli.add_command("netfilter config enable", self.enable)
        self.cli.add_command("netfilter config disable", self.disable)

        self.cli.add_command("netfilter config zone add :zone!", self.add_zone)
        self.cli.add_command("netfilter config zone remove :zone!", self.remove_zone)
        self.cli.add_command(
            "netfilter config zone interface add :zone :interface",
            self.add_zone_interface,
        )
        self.cli.add_command(
            "netfilter config zone interface remove :zone :interface!zone-interface",
            self.remove_zone_interface,
        )

        self.cli.add_command(
            "netfilter config masquerade add :interface", self.add_masquerade
        )
        self.cli.add_command(
            "netfilter config masquerade remove :interface!masquerade-interface",
            self.add_masquerade,
        )
        self.cli.add_command(
            "netfilter config masquerade ip-forward add :interface!masquerade-interface :destination",
            self.add_masquerade_forward,
        )
        self.cli.add_command(
            "netfilter config masquerade ip-forward remove :interface!masquerade-interface :destination!masquerade-destination",
            self.remove_masquerade_forward,
        )
        self.cli.add_command(
            "netfilter config masquerade ip-forward-port add :interface!masquerade-interface :destination!masquerade-destination :protocol!ip-forward-protocol :port :destination-port",
            self.add_masquerade_port,
        )
        self.cli.add_command(
            "netfilter config masquerade ip-forward-port remove :interface!masquerade-interface :destination!masquerade-destination :protocol!ip-forward-protocol :port!masquerade-port",
            self.remove_masquerade_port,
        )

        self.cli.add_command(
            "netfilter config input policy :policy", self.set_input_policy
        )

        self.cli.add_command("netfilter config input rule list", self.list_input_rules)
        self.cli.add_command(
            "netfilter config input rule add :description :verdict", self.add_input_rule
        )
        self.cli.add_command(
            "netfilter config input rule update :input-rule @description @verdict",
            self.update_input_rule,
        )
        self.cli.add_command(
            "netfilter config input rule remove :input-rule", self.remove_input_rule
        )

        self.cli.add_command(
            "netfilter config input rule zone add :input-rule :zone",
            self.add_input_rule_zone,
        )
        self.cli.add_command(
            "netfilter config input rule zone remove :input-rule :zone!input-rule-zone",
            self.remove_input_rule_zone,
        )

        self.cli.add_command(
            "netfilter config input rule ip-match add :input-rule *source *destination *protocol @negate",
            self.add_input_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match list :input-rule",
            self.list_input_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match update :input-rule :input-rule-ip-match *source *destination *protocol @negate",
            self.update_input_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match remove :input-rule :input-rule-ip-match",
            self.remove_input_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match source add :input-rule :input-rule-ip-match :source",
            self.add_input_rule_ip_source,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match source remove :input-rule :input-rule-ip-match :source",
            self.remove_input_rule_ip_source,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match destination add :input-rule :input-rule-ip-match :destination",
            self.add_input_rule_ip_destination,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match destination remove :input-rule :input-rule-ip-match :destination",
            self.remove_input_rule_ip_destination,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match protocol add :input-rule :input-rule-ip-match !protocol",
            self.add_input_rule_ip_protocol,
        )
        self.cli.add_command(
            "netfilter config input rule ip-match protocol remove :input-rule :input-rule-ip-match :protocol",
            self.remove_input_rule_ip_protocol,
        )

        self.cli.add_command(
            "netfilter config input rule ip6-match add :input-rule! *source *destination *protocol @negate",
            self.add_input_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match list :input-rule",
            self.list_input_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match update :input-rule :input-rule-ip6-match *source *destination *protocol @negate",
            self.update_input_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match remove :input-rule :input-rule-ip6-match",
            self.remove_input_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match source add :input-rule :input-rule-ip6-match :source",
            self.add_input_rule_ip6_source,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match source remove :input-rule :input-rule-ip6-match :source",
            self.remove_input_rule_ip6_source,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match destination add :input-rule :input-rule-ip6-match :destination",
            self.add_input_rule_ip6_destination,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match destination remove :input-rule :input-rule-ip6-match :destination",
            self.remove_input_rule_ip6_destination,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match protocol add :input-rule :input-rule-ip6-match :protocol",
            self.add_input_rule_ip6_protocol,
        )
        self.cli.add_command(
            "netfilter config input rule ip6-match protocol remove :input-rule :input-rule-ip6-match :protocol",
            self.remove_input_rule_ip6_protocol,
        )

        self.cli.add_command(
            "netfilter config input rule tcp-match add :input-rule *source *destination @negate",
            self.add_input_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match list :input-rule",
            self.list_input_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match update :input-rule :input-rule-tcp-match *source *destination @negate",
            self.update_input_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match remove :input-rule :input-rule-tcp-match",
            self.remove_input_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match source add :input-rule :input-rule-tcp-match :source",
            self.add_input_rule_tcp_source,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match source remove :input-rule :input-rule-tcp-match :source",
            self.remove_input_rule_tcp_source,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match destination add :input-rule :input-rule-tcp-match :destination",
            self.add_input_rule_tcp_destination,
        )
        self.cli.add_command(
            "netfilter config input rule tcp-match destination remove :input-rule :input-rule-tcp-match :destination",
            self.remove_input_rule_tcp_destination,
        )

        self.cli.add_command(
            "netfilter config input rule udp-match add :input-rule *source *destination @negate",
            self.add_input_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match list :input-rule",
            self.list_input_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match update :input-rule :input-rule-udp-match *source *destination @negate",
            self.update_input_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match remove :input-rule :input-rule-udp-match",
            self.remove_input_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match source add :input-rule :input-rule-udp-match :source",
            self.add_input_rule_udp_source,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match source remove :input-rule :input-rule-udp-match :source",
            self.remove_input_rule_udp_source,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match destination add :input-rule :input-rule-udp-match :destination",
            self.add_input_rule_udp_destination,
        )
        self.cli.add_command(
            "netfilter config input rule udp-match destination remove :input-rule :input-rule-udp-match :destination",
            self.remove_input_rule_udp_destination,
        )

        self.cli.add_command(
            "netfilter config input rule icmp-match add :input-rule *type *code @negate",
            self.add_input_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match list :input-rule",
            self.list_input_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match update :input-rule :input-rule-icmp-match *type *code @negate",
            self.update_input_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match remove :input-rule :input-rule-icmp-match",
            self.remove_input_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match type add :input-rule :input-rule-icmp-match :type",
            self.add_input_rule_icmp_type,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match type remove :input-rule :input-rule-icmp-match :type",
            self.remove_input_rule_icmp_type,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match code add :input-rule :input-rule-icmp-match :code",
            self.add_input_rule_icmp_code,
        )
        self.cli.add_command(
            "netfilter config input rule icmp-match code remove :input-rule :input-rule-icmp-match :code",
            self.remove_input_rule_icmp_code,
        )

        self.cli.add_command(
            "netfilter config input rule icmp6-match add :input-rule *type *code @negate",
            self.add_input_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match list :input-rule",
            self.list_input_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match update :input-rule :input-rule-icmp6-match *type *code @negate",
            self.update_input_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match remove :input-rule :input-rule-icmp6-match",
            self.remove_input_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match type add :input-rule :input-rule-icmp6-match :type",
            self.add_input_rule_icmp6_type,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match type remove :input-rule :input-rule-icmp6-match :type",
            self.remove_input_rule_icmp6_type,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match code add :input-rule :input-rule-icmp6-match :code",
            self.add_input_rule_icmp6_code,
        )
        self.cli.add_command(
            "netfilter config input rule icmp6-match code remove :input-rule :input-rule-icmp6-match :code",
            self.remove_input_rule_icmp6_code,
        )

        self.cli.add_command(
            "netfilter config input rule ct-match add :input-rule *state @negate",
            self.add_input_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config input rule ct-match list :input-rule :input-rule-ct-match",
            self.list_input_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config input rule ct-match update :input-rule :input-rule-ct-match *state @negate",
            self.update_input_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config input rule ct-match remove :input-rule :input-rule-ct-match",
            self.remove_input_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config input rule ct-match state add :input-rule :input-rule-ct-match :state",
            self.add_input_rule_ct_state,
        )
        self.cli.add_command(
            "netfilter config input rule ct-match state remove :input-rule :input-rule-ct-match :state",
            self.remove_input_rule_ct_state,
        )

        self.cli.add_command(
            "netfilter config input rule meta-match add :input-rule *input-interface *protocol @negate",
            self.add_input_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match list :input-rule",
            self.list_input_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match update :input-rule :input-rule-meta-match *input-interface *protocol @negate",
            self.update_input_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match remove :input-rule :input-rule-meta-match",
            self.remove_input_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match input-interface add :input-rule :input-rule-meta-match :input-interface",
            self.add_input_rule_meta_input_interface,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match input-interface remove :input-rule :input-rule-meta-match :input-interface",
            self.remove_input_rule_meta_input_interface,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match protocol add :input-rule :input-rule-meta-match :protocol",
            self.add_input_rule_meta_protocol,
        )
        self.cli.add_command(
            "netfilter config input rule meta-match protocol remove :input-rule :input-rule-meta-match :protocol",
            self.remove_input_rule_meta_protocol,
        )

        self.cli.add_command(
            "netfilter config forward policy :policy", self.set_forward_policy
        )

        self.cli.add_command(
            "netfilter config forward rule list", self.list_forward_rules
        )
        self.cli.add_command(
            "netfilter config forward rule add :description :verdict",
            self.add_forward_rule,
        )
        self.cli.add_command(
            "netfilter config forward rule update :forward-rule @description @verdict",
            self.update_forward_rule,
        )
        self.cli.add_command(
            "netfilter config forward rule remove :forward-rule",
            self.remove_forward_rule,
        )

        self.cli.add_command(
            "netfilter config forward rule source-zone add :forward-rule :zone",
            self.add_forward_rule_source_zone,
        )
        self.cli.add_command(
            "netfilter config forward rule source-zone remove :forward-rule :zone!forward-rule-zone",
            self.remove_forward_rule_source_zone,
        )

        self.cli.add_command(
            "netfilter config forward rule destination-zone add :forward-rule :zone",
            self.add_forward_rule_destination_zone,
        )
        self.cli.add_command(
            "netfilter config forward rule destination-zone remove :forward-rule :zone!forward-rule-zone",
            self.remove_forward_rule_destination_zone,
        )

        self.cli.add_command(
            "netfilter config forward rule ip-match add :forward-rule *source *destination *protocol @negate",
            self.add_forward_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match list :forward-rule",
            self.list_forward_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match update :forward-rule :forward-rule-ip-match *source *destination *protocol @negate",
            self.update_forward_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match remove :forward-rule :forward-rule-ip-match",
            self.remove_forward_rule_ip_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match source add :forward-rule :forward-rule-ip-match :source",
            self.add_forward_rule_ip_source,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match source remove :forward-rule :forward-rule-ip-match :source",
            self.remove_forward_rule_ip_source,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match destination add :forward-rule :forward-rule-ip-match :destination",
            self.add_forward_rule_ip_destination,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match destination remove :forward-rule :forward-rule-ip-match :destination",
            self.remove_forward_rule_ip_destination,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match protocol add :forward-rule :forward-rule-ip-match !protocol",
            self.add_forward_rule_ip_protocol,
        )
        self.cli.add_command(
            "netfilter config forward rule ip-match protocol remove :forward-rule :forward-rule-ip-match :protocol",
            self.remove_forward_rule_ip_protocol,
        )

        self.cli.add_command(
            "netfilter config forward rule ip6-match add :forward-rule! *source *destination *protocol @negate",
            self.add_forward_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match list :forward-rule",
            self.list_forward_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match update :forward-rule :forward-rule-ip6-match *source *destination *protocol @negate",
            self.update_forward_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match remove :forward-rule :forward-rule-ip6-match",
            self.remove_forward_rule_ip6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match source add :forward-rule :forward-rule-ip6-match :source",
            self.add_forward_rule_ip6_source,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match source remove :forward-rule :forward-rule-ip6-match :source",
            self.remove_forward_rule_ip6_source,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match destination add :forward-rule :forward-rule-ip6-match :destination",
            self.add_forward_rule_ip6_destination,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match destination remove :forward-rule :forward-rule-ip6-match :destination",
            self.remove_forward_rule_ip6_destination,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match protocol add :forward-rule :forward-rule-ip6-match :protocol",
            self.add_forward_rule_ip6_protocol,
        )
        self.cli.add_command(
            "netfilter config forward rule ip6-match protocol remove :forward-rule :forward-rule-ip6-match :protocol",
            self.remove_forward_rule_ip6_protocol,
        )

        self.cli.add_command(
            "netfilter config forward rule tcp-match add :forward-rule *source *destination @negate",
            self.add_forward_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match list :forward-rule",
            self.list_forward_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match update :forward-rule :forward-rule-tcp-match *source *destination @negate",
            self.update_forward_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match remove :forward-rule :forward-rule-tcp-match",
            self.remove_forward_rule_tcp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match source add :forward-rule :forward-rule-tcp-match :source",
            self.add_forward_rule_tcp_source,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match source remove :forward-rule :forward-rule-tcp-match :source",
            self.remove_forward_rule_tcp_source,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match destination add :forward-rule :forward-rule-tcp-match :destination",
            self.add_forward_rule_tcp_destination,
        )
        self.cli.add_command(
            "netfilter config forward rule tcp-match destination remove :forward-rule :forward-rule-tcp-match :destination",
            self.remove_forward_rule_tcp_destination,
        )

        self.cli.add_command(
            "netfilter config forward rule udp-match add :forward-rule *source *destination @negate",
            self.add_forward_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match list :forward-rule",
            self.list_forward_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match update :forward-rule :forward-rule-udp-match *source *destination @negate",
            self.update_forward_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match remove :forward-rule :forward-rule-udp-match",
            self.remove_forward_rule_udp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match source add :forward-rule :forward-rule-udp-match :source",
            self.add_forward_rule_udp_source,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match source remove :forward-rule :forward-rule-udp-match :source",
            self.remove_forward_rule_udp_source,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match destination add :forward-rule :forward-rule-udp-match :destination",
            self.add_forward_rule_udp_destination,
        )
        self.cli.add_command(
            "netfilter config forward rule udp-match destination remove :forward-rule :forward-rule-udp-match :destination",
            self.remove_forward_rule_udp_destination,
        )

        self.cli.add_command(
            "netfilter config forward rule icmp-match add :forward-rule *type *code @negate",
            self.add_forward_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match list :forward-rule",
            self.list_forward_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match update :forward-rule :forward-rule-icmp-match *type *code @negate",
            self.update_forward_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match remove :forward-rule :forward-rule-icmp-match",
            self.remove_forward_rule_icmp_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match type add :forward-rule :forward-rule-icmp-match :type",
            self.add_forward_rule_icmp_type,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match type remove :forward-rule :forward-rule-icmp-match :type",
            self.remove_forward_rule_icmp_type,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match code add :forward-rule :forward-rule-icmp-match :code",
            self.add_forward_rule_icmp_code,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp-match code remove :forward-rule :forward-rule-icmp-match :code",
            self.remove_forward_rule_icmp_code,
        )

        self.cli.add_command(
            "netfilter config forward rule icmp6-match add :forward-rule *type *code @negate",
            self.add_forward_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match list :forward-rule",
            self.list_forward_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match update :forward-rule :forward-rule-icmp6-match *type *code @negate",
            self.update_forward_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match remove :forward-rule :forward-rule-icmp6-match",
            self.remove_forward_rule_icmp6_match,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match type add :forward-rule :forward-rule-icmp6-match :type",
            self.add_forward_rule_icmp6_type,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match type remove :forward-rule :forward-rule-icmp6-match :type",
            self.remove_forward_rule_icmp6_type,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match code add :forward-rule :forward-rule-icmp6-match :code",
            self.add_forward_rule_icmp6_code,
        )
        self.cli.add_command(
            "netfilter config forward rule icmp6-match code remove :forward-rule :forward-rule-icmp6-match :code",
            self.remove_forward_rule_icmp6_code,
        )

        self.cli.add_command(
            "netfilter config forward rule ct-match add :forward-rule *state @negate",
            self.add_forward_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ct-match list :forward-rule :forward-rule-ct-match",
            self.list_forward_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ct-match update :forward-rule :forward-rule-ct-match *state @negate",
            self.update_forward_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ct-match remove :forward-rule :forward-rule-ct-match",
            self.remove_forward_rule_ct_match,
        )
        self.cli.add_command(
            "netfilter config forward rule ct-match state add :forward-rule :forward-rule-ct-match :state",
            self.add_forward_rule_ct_state,
        )
        self.cli.add_command(
            "netfilter config forward rule ct-match state remove :forward-rule :forward-rule-ct-match :state",
            self.remove_forward_rule_ct_state,
        )

        self.cli.add_command(
            "netfilter config forward rule meta-match add :forward-rule *input-interface *protocol @negate",
            self.add_forward_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match list :forward-rule",
            self.list_forward_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match update :forward-rule :forward-rule-meta-match *input-interface *protocol @negate",
            self.update_forward_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match remove :forward-rule :forward-rule-meta-match",
            self.remove_forward_rule_meta_match,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match input-interface add :forward-rule :forward-rule-meta-match :input-interface",
            self.add_forward_rule_meta_input_interface,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match input-interface remove :forward-rule :forward-rule-meta-match :input-interface",
            self.remove_forward_rule_meta_input_interface,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match output-interface add :forward-rule :forward-rule-meta-match :output-interface",
            self.add_forward_rule_meta_output_interface,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match output-interface remove :forward-rule :forward-rule-meta-match :output-interface",
            self.remove_forward_rule_meta_output_interface,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match protocol add :forward-rule :forward-rule-meta-match :protocol",
            self.add_forward_rule_meta_protocol,
        )
        self.cli.add_command(
            "netfilter config forward rule meta-match protocol remove :forward-rule :forward-rule-meta-match :protocol",
            self.remove_forward_rule_meta_protocol,
        )

    async def complete_protocol(self):
        return netfilter_pb2.IPForwardProtocol.keys()

    async def complete_zone(self):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        for zone in config.zone:
            completions.append(zone.name)
        return completions

    async def complete_zone_interface(self, zone: str = None):
        completions = []
        if zone is None:
            return completions
        config = await self.rpc.request("netfilter/config/get")
        for zone_item in config.zone:
            if zone_item.name == zone:
                break
        else:
            return completions
        for interface in zone_item.interface:
            completions.append(interface)
        return completions

    async def complete_masquerade_interface(self):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        for masquerade in config.masquerade:
            completions.append(masquerade.interface)
        return completions

    async def complete_masquerade_destination(self, interface: str = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")

        if interface is None:
            return completions

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                break
        else:
            return completions

        for ip_forward in masquerade.ip_forward:
            completions.append(ip_forward.destination)

        return completions

    async def complete_masquerade_port(
        self,
        interface: str = None,
        destination: IPv4Address = None,
        protocol: str = None,
        **args,
    ):
        completions = []
        config = await self.rpc.request("netfilter/config/get")

        if interface is None:
            return completions

        if destination is None:
            return completions
        destination = str(destination)

        if protocol is None:
            return completions

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                for ip_forward in masquerade.ip_forward:
                    if ip_forward.destination == destination:
                        for port_map in ip_forward.port_map:
                            if port_map.protocol == protocol:
                                completions.append(port_map.port)
                        return completions
        else:
            return completions

    async def complete_policy(self):
        return netfilter_pb2.Policy.keys()

    async def complete_verdict(self):
        return netfilter_pb2.Rule.Verdict.keys()

    async def complete_input_rule(self):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        for order, rule in enumerate(config.input.rule):
            completions.append(
                Completion(str(order), display="%s %s" % (order, rule.description))
            )
        return completions

    async def complete_input_rule_zone(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
        for zone in rule.source_zone:
            completions.append(zone)
        return completions

    async def show(self) -> netfilter_pb2.NetfilterConfig:
        return await self.rpc.request("netfilter/config/get")

    async def enable(self):
        config = await self.rpc.request("netfilter/config/get")
        config.enabled = True
        await self.rpc.request("netfilter/config/update", config)

    async def disable(self):
        config = await self.rpc.request("netfilter/config/get")
        config.enabled = False
        await self.rpc.request("netfilter/config/update", config)

    async def add_zone(self, zone: str):
        config = await self.rpc.request("netfilter/config/get")

        for entry in config.zone:
            if entry.name == zone:
                raise InvalidArgument("Zone already exists")

        entry = config.zone.add()
        entry.name = zone
        await self.rpc.request("netfilter/config/update", config)

    async def remove_zone(self, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        for i, entry in enumerate(config.zone):
            if entry.name == zone:
                del config.zone[i]
                break
        await self.rpc.request("netfilter/config/update", config)

    def get_zone(self, config, name: str):
        for zone in config.zone:
            if zone.name == name:
                return zone
        raise InvalidArgument("Zone %s does not exist" % name)

    async def add_zone_interface(self, zone: str, interface: str):
        config = await self.rpc.request("netfilter/config/get")
        zone = self.get_zone(config, zone)
        for zone_interface in zone.interface:
            if zone_interface == interface:
                raise InvalidArgument(
                    "Interface %s already exists in zone %s" % (interface, zone.name)
                )
        zone.interface.append(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_zone_interface(self, zone: str, interface: str):
        config = await self.rpc.request("netfilter/config/get")
        zone = self.get_zone(config, zone)
        for i, zone_interface in enumerate(zone.interface):
            if zone_interface == interface:
                del zone.interface[i]
                break
        await self.rpc.request("netfilter/config/update", config)

    async def add_masquerade(self, interface: str):
        config = await self.rpc.request("netfilter/config/get")

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                raise InvalidArgument("Masqeurade already exists")

        masquerade = config.masquerade.add()
        masquerade.interface = interface
        await self.rpc.request("netfilter/config/update", config)

    async def remove_masquerade(self, interface: str):
        config = await self.rpc.request("netfilter/config/get")
        for i, masquerade in enumerate(config.masquerade):
            if masquerade.interface == interface:
                del config.masquerade[i]
                break
        await self.rpc.request("netfilter/config/update", config)

    async def add_masquerade_forward(self, interface: str, destination: IPv4Address):
        config = await self.rpc.request("netfilter/config/get")

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                ip_forward = masquerade.ip_forward.add()
                ip_forward.destination = str(destination)

        await self.rpc.request("netfilter/config/update", config)

    async def remove_masquerade_forward(self, interface: str, destination: IPv4Address):
        config = await self.rpc.request("netfilter/config/get")

        destination = str(destination)

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                for i, ip_forward in enumerate(masquerade.ip_forward):
                    if ip_forward.destination == destination:
                        del masquerade.ip_forward[i]
                        break

        await self.rpc.request("netfilter/config/update", config)

    async def add_masquerade_port(
        self,
        interface: str,
        destination: IPv4Address,
        protocol: str,
        port: UInt16,
        destination_port=None,
    ):
        protocol = netfilter_pb2.IPForwardProtocol.Value(protocol)
        config = await self.rpc.request("netfilter/config/get")

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                for ip_forward in masquerade.ip_forward:
                    if ip_forward.destination == destination:
                        port_map = ip_forward.port_map.add()
                        port_map.port = port
                        port_map.protocol = protocol
                        if destination_port:
                            port_map.destination_port = destination_port
                        break
                else:
                    raise InvalidArgument("Masquerade destination does not exist")
                break
        else:
            raise InvalidArgument("Masquerade interface does not exist")

        await self.rpc.request("netfilter/config/update", config)

    async def remove_masquerade_port(
        self,
        interface: str,
        destination: IPv4Address,
        protocol: str,
        port: UInt16,
    ):
        protocol = netfilter_pb2.IPForwardProtocol.Value(protocol)
        config = await self.rpc.request("netfilter/config/get")

        for masquerade in config.masquerade:
            if masquerade.interface == interface:
                for ip_forward in masquerade.ip_forward:
                    if ip_forward.destination == destination:
                        for i, port_map in enumerate(ip_forward.port_map):
                            if port_map.protocol == protocol and port_map.port == port:
                                del ip_forward.port_map[i]
                                break
                        else:
                            raise InvalidArgument("Masquerade port does not exist")
                        break
                else:
                    raise InvalidArgument("Masquerade destination does not exist")
                break
        else:
            raise InvalidArgument("Masquerade interface does not exist")

        await self.rpc.request("netfilter/config/update", config)

    async def set_input_policy(self, policy: str):
        policy = netfilter_pb2.Policy.Value(policy)
        config = await self.rpc.request("netfilter/config/get")
        config.input.policy = policy
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rules(self):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        for i, rule in enumerate(config.input.rule):
            s += f"{i}:\n{textwrap.indent(str(rule), '    ')}"
        return s

    async def add_input_rule(self, description: str, verdict: str):
        if verdict not in ("ACCEPT", "DROP"):
            raise InvalidArgument(f"Invalid verdict {verdict}")
        verdict = netfilter_pb2.Rule.Verdict.Value(verdict)
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule.add()
        rule.description = description
        rule.verdict = verdict
        await self.rpc.request("netfilter/config/update", config)

    async def update_input_rule(
        self,
        input_rule: UInt32,
        description: str = None,
        verdict: str = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        if description is not None:
            rule.description = description
        if verdict is not None:
            if verdict not in ("ACCEPT", "DROP"):
                raise InvalidArgument(f"Invalid verdict {verdict}")
            rule.verdict = netfilter_pb2.Rule.Verdict.Value(verdict)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule(self, input_rule: int):
        config = await self.rpc.request("netfilter/config/get")
        del config.input.rule[input_rule]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_zone(self, input_rule: int, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for zone_config in config.zone:
            if zone_config.name == zone:
                break
        else:
            raise InvalidArgument("Zone %s does not exist" % zone)
        for rule_zone in rule.source_zone:
            if rule_zone == zone:
                raise InvalidArgument("Zone %s is already set on rule" % zone)
        rule.source_zone.append(zone)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_zone(self, input_rule: int, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, zone_name in enumerate(rule.source_zone):
            if zone_name == zone:
                del rule.source_zone[i]
                break
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip_match(
        self,
        input_rule: int,
        source: list[IPv4Network | IPv6Network] = [],
        destination: list[IPv4Network | IPv6Network] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip.add()
        for network in source:
            match.source.append(str(network))
        for network in destination:
            match.destination.append(str(network))
        match.protocol = protocol
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_ip_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.ip):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_ip_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_ip_match(
        self,
        input_rule: int,
        input_rule_ip_match: int,
        source: list[IPv4Network | IPv6Network] = None,
        destination: list[IPv4Network | IPv6Network] = None,
        protocol: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        if source is not None:
            for network in source:
                match.source.append(str(network))
        if destination is not None:
            for network in destination:
                match.destination.append(str(network))
        if protocol is not None:
            match.protocol = protocol
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip_match(
        self, input_rule: int, input_rule_ip_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.ip[input_rule_ip_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip_source(
        self, input_rule: int, input_rule_ip_match: int, source: IPv4Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        match.source.append(source)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip_source(
        self, input_rule: int, input_rule_ip_match: int, source: IPv4Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        match.source.remove(source)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip_destination(
        self, input_rule: int, input_rule_ip_match: int, destination: IPv4Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        match.destination.append(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip_destination(
        self, input_rule: int, input_rule_ip_match: int, destination: IPv4Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        match.destination.remove(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip_protocol(
        self, input_rule: int, input_rule_ip_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        match.protocol.append(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip_protocol(
        self, input_rule: int, input_rule_ip_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip[input_rule_ip_match]
        match.protocol.remove(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip6_match(
        self,
        input_rule: int,
        source: list[IPv4Network | IPv6Address] = [],
        destination: list[IPv4Network | IPv6Address] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6.add()
        for network in source:
            match.source.append(str(network))
        for network in destination:
            match.destination.append(str(network))
        match.protocol = protocol
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_ip6_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.ip6):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_ip6_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_ip6_match(
        self,
        input_rule: int,
        input_rule_ip6_match: int,
        source: list[IPv4Network | IPv6Network] = None,
        destination: list[IPv4Network | IPv6Network] = None,
        protocol: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        if source is not None:
            for network in source:
                match.source.append(str(network))
        if destination is not None:
            for network in destination:
                match.destination.append(str(network))
        if protocol is not None:
            match.protocol = protocol
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip6_match(
        self, input_rule: int, input_rule_ip6_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.ip6[input_rule_ip6_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip6_source(
        self,
        input_rule: int,
        input_rule_ip6_match: int,
        source: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        match.source.append(str(source))
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip6_source(
        self,
        input_rule: int,
        input_rule_ip6_match: int,
        source: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        match.source.remove(str(source))
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip6_destination(
        self,
        input_rule: int,
        input_rule_ip6_match: int,
        destination: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        match.destination.append(str(destination))
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip6_destination(
        self,
        input_rule: int,
        input_rule_ip6_match: int,
        destination: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        match.destination.remove(str(destination))
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ip6_protocol(
        self, input_rule: int, input_rule_ip6_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        match.protocol.append(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ip6_protocol(
        self, input_rule: int, input_rule_ip6_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ip6[input_rule_ip6_match]
        match.protocol.remove(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_tcp_match(
        self,
        input_rule: int,
        source: list[int] = [],
        destination: list[int] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.tcp.add()
        match.source = source
        match.destination = destination
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_tcp_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.tcp):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_tcp_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_tcp_match(
        self,
        input_rule: int,
        input_rule_tcp_match: int,
        source: list[int] = None,
        destination: list[int] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.tcp[input_rule_tcp_match]
        if source is not None:
            match.source = source
        if destination is not None:
            match.destination = destination
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_tcp_match(
        self, input_rule: int, input_rule_tcp_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.tcp[input_rule_tcp_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_tcp_source(
        self, input_rule: int, input_rule_tcp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.tcp[input_rule_tcp_match]
        match.source.append(source)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_tcp_source(
        self, input_rule: int, input_rule_tcp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.tcp[input_rule_tcp_match]
        match.source.remove(source)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_tcp_destination(
        self, input_rule: int, input_rule_tcp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.tcp[input_rule_tcp_match]
        match.destination.append(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_tcp_destination(
        self, input_rule: int, input_rule_tcp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.tcp[input_rule_tcp_match]
        match.destination.remove(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_udp_match(
        self,
        input_rule: int,
        source: list[int] = [],
        destination: list[int] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.udp.add()
        match.source = source
        match.destination = destination
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_udp_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.udp):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_udp_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_udp_match(
        self,
        input_rule: int,
        input_rule_udp_match: int,
        source: list[int] = None,
        destination: list[int] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.udp[input_rule_udp_match]
        if source is not None:
            match.source = source
        if destination is not None:
            match.destination = destination
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_udp_match(
        self, input_rule: int, input_rule_udp_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.udp[input_rule_udp_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_udp_source(
        self, input_rule: int, input_rule_udp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.udp[input_rule_udp_match]
        match.source.append(source)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_udp_source(
        self, input_rule: int, input_rule_udp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.udp[input_rule_udp_match]
        match.source.remove(source)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_udp_destination(
        self, input_rule: int, input_rule_udp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.udp[input_rule_udp_match]
        match.destination.append(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_udp_destination(
        self, input_rule: int, input_rule_udp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.udp[input_rule_udp_match]
        match.destination.remove(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_icmp_match(
        self,
        input_rule: int,
        type: list[str] = [],
        code: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp.add()
        match.type = type
        match.code = code
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_icmp_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.icmp):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_icmp_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_icmp_match(
        self,
        input_rule: int,
        input_rule_icmp_match: int,
        type: list[str] = None,
        code: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp[input_rule_icmp_match]
        if type is not None:
            match.type = type
        if code is not None:
            match.code = code
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_icmp_match(
        self, input_rule: int, input_rule_icmp_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.icmp[input_rule_icmp_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_icmp_type(
        self, input_rule: int, input_rule_icmp_match: int, type: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp[input_rule_icmp_match]
        match.type.append(type)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_icmp_type(
        self, input_rule: int, input_rule_icmp_match: int, type: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp[input_rule_icmp_match]
        match.type.remove(type)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_icmp_code(
        self, input_rule: int, input_rule_icmp_match: int, code: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp[input_rule_icmp_match]
        match.code.append(code)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_icmp_code(
        self, input_rule: int, input_rule_icmp_match: int, code: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp[input_rule_icmp_match]
        match.code.remove(code)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_icmp6_match(
        self,
        input_rule: int,
        type: list[str] = [],
        code: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp6.add()
        match.type = type
        match.code = code
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_icmp6_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.icmp6):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_icmp6_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_icmp6_match(
        self,
        input_rule: int,
        input_rule_icmp6_match,
        type: list[str] = None,
        code: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp6[input_rule_icmp6_match]
        if type is not None:
            match.type = type
        if code is not None:
            match.code = code
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_icmp6_match(
        self, input_rule: int, input_rule_icmp6_match
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.icmp6[input_rule_icmp6_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_icmp6_type(
        self, input_rule: int, input_rule_icmp6_match, type: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp6[input_rule_icmp6_match]
        match.type.append(type)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_icmp6_type(
        self, input_rule: int, input_rule_icmp6_match, type: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp6[input_rule_icmp6_match]
        match.type.remove(type)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_icmp6_code(
        self, input_rule: int, input_rule_icmp6_match, code: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp6[input_rule_icmp6_match]
        match.code.append(code)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_icmp6_code(
        self, input_rule: int, input_rule_icmp6_match, code: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.icmp6[input_rule_icmp6_match]
        match.code.remove(code)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ct_match(
        self, input_rule: int, state: list[str] = [], negate: bool = False
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ct.add()
        match.state = state
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_ct_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.ct):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_ct_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
        for order, match in enumerate(rule.ct):
            desc = ""
            if match.negate:
                desc += "! "
            if match.state:
                desc += "state=%s " % ",".join(match.state)
            completions.append(Completion(str(order), display="%s %s" % (order, desc)))
        return completions

    async def update_input_rule_ct_match(
        self,
        input_rule: int,
        input_rule_ct_match: int,
        state: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ct[input_rule_ct_match]
        if state is not None:
            match.state = state
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ct_match(
        self, input_rule: int, input_rule_ct_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.ct[input_rule_ct_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_ct_state(
        self, input_rule: int, input_rule_ct_match: int, state: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ct[input_rule_ct_match]
        match.state.append(state)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_ct_state(
        self, input_rule: int, input_rule_ct_match: int, state: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.ct[input_rule_ct_match]
        match.state.remove(state)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_meta_match(
        self,
        input_rule: int,
        input_interface: list[str] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.meta.add()
        match.input_interface = input_interface
        match.protocol = protocol
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_input_rule_meta_match(self, input_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        for i, match in enumerate(rule.meta):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_input_rule_meta_match(self, input_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if input_rule is None or input_rule >= len(config.input.rule):
            return completions
        rule = config.input.rule[input_rule]
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

    async def update_input_rule_meta_match(
        self,
        input_rule: int,
        input_rule_meta_match,
        input_interface: list[str] = None,
        protocol: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.meta[input_rule_meta_match]
        if input_interface is not None:
            match.input_interface = input_interface
        if protocol is not None:
            match.protocol = protocol
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_meta_match(
        self, input_rule: int, input_rule_meta_match
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        del rule.meta[input_rule_meta_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_meta_input_interface(
        self, input_rule: int, input_rule_meta_match, interface: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.meta[input_rule_meta_match]
        match.input_interface.append(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_meta_input_interface(
        self, input_rule: int, input_rule_meta_match, interface: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.meta[input_rule_meta_match]
        match.input_interface.remove(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def add_input_rule_meta_protocol(
        self, input_rule: int, input_rule_meta_match, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.meta[input_rule_meta_match]
        match.protocol.append(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_input_rule_meta_protocol(
        self, input_rule: int, input_rule_meta_match, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[input_rule]
        match = rule.meta[input_rule_meta_match]
        match.protocol.remove(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def set_forward_policy(self, policy: netfilter_pb2.Policy):
        config = await self.rpc.request("netfilter/config/get")
        config.forward.policy = policy
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rules(self):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        for i, rule in enumerate(config.forward.rule):
            s += f"{i}:\n{textwrap.indent(str(rule), '    ')}"
        return s

    async def add_forward_rule(self, description: str, verdict: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule.add()
        rule.description = description
        rule.verdict = verdict
        await self.rpc.request("netfilter/config/update", config)

    async def complete_forward_rule(self):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        for order, rule in enumerate(config.forward.rule):
            completions.append(
                Completion(str(order), display="%s %s" % (order, rule.description))
            )
        return completions

    async def update_forward_rule(
        self,
        forward_rule: UInt32,
        description: str = None,
        verdict: str = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        if description is not None:
            rule.description = description
        if verdict is not None:
            if verdict not in ("ACCEPT", "DROP"):
                raise InvalidArgument(f"Invalid verdict {verdict}")
            rule.verdict = netfilter_pb2.Rule.Verdict.Value(verdict)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule(self, forward_rule: int):
        config = await self.rpc.request("netfilter/config/get")
        del config.forward.rule[forward_rule]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_source_zone(self, forward_rule: int, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for zone_config in config.zone:
            if zone_config.name == zone:
                break
        else:
            raise InvalidArgument("Zone %s does not exist" % zone)
        for rule_zone in rule.source_zone:
            if rule_zone == zone:
                raise InvalidArgument("Zone %s is already set on rule" % zone)
        rule.source_zone.append(zone)
        await self.rpc.request("netfilter/config/update", config)

    async def complete_forward_rule_zone(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
        for zone in rule.source_zone:
            completions.append(zone)
        return completions

    async def remove_forward_rule_source_zone(self, forward_rule: int, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, zone_name in enumerate(rule.source_zone):
            if zone_name == zone:
                del rule.source_zone[i]
                break
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_destination_zone(self, forward_rule: int, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for zone_config in config.zone:
            if zone_config.name == zone:
                break
        else:
            raise InvalidArgument("Zone %s does not exist" % zone)
        for rule_zone in rule.destination_zone:
            if rule_zone == zone:
                raise InvalidArgument("Zone %s is already set on rule" % zone)
        rule.destination_zone.append(zone)
        await self.rpc.request("netfilter/config/update", config)

    async def complete_forward_rule_zone(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
        for zone in rule.destination_zone:
            completions.append(zone)
        return completions

    async def remove_forward_rule_destination_zone(self, forward_rule: int, zone: str):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, zone_name in enumerate(rule.destination_zone):
            if zone_name == zone:
                del rule.destination_zone[i]
                break
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip_match(
        self,
        forward_rule: int,
        source: list[IPv4Network | IPv6Network] = [],
        destination: list[IPv4Network | IPv6Network] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip.add()
        for address in source:
            match.source.append(str(address))
        for address in destination:
            match.destination.append(str(address))
        match.protocol = protocol
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_ip_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.ip):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_ip_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_ip_match(
        self,
        forward_rule: int,
        forward_rule_ip_match: int,
        source: list[IPv4Network | IPv6Address] = [],
        destination: list[IPv4Network | IPv6Address] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        if source is not None:
            for network in source:
                match.source.append(str(network))
        if destination is not None:
            for network in destination:
                match.destination.append(str(network))
        if protocol is not None:
            match.protocol = protocol
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip_match(
        self, forward_rule: int, forward_rule_ip_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.ip[forward_rule_ip_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip_source(
        self,
        forward_rule: int,
        forward_rule_ip_match: int,
        source: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        match.source.append(str(source))
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip_source(
        self,
        forward_rule: int,
        forward_rule_ip_match: int,
        source: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        match.source.remove(str(source))
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip_destination(
        self,
        forward_rule: int,
        forward_rule_ip_match: int,
        destination: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        match.destination.append(str(destination))
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip_destination(
        self,
        forward_rule: int,
        forward_rule_ip_match: int,
        destination: IPv4Network | IPv6Network,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        match.destination.remove(str(destination))
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip_protocol(
        self, forward_rule: int, forward_rule_ip_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        match.protocol.append(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip_protocol(
        self, forward_rule: int, forward_rule_ip_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip[forward_rule_ip_match]
        match.protocol.remove(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip6_match(
        self,
        forward_rule: int,
        source: list[IPv4Network | IPv6Network] = [],
        destination: list[IPv4Network | IPv6Network] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6.add()
        for network in source:
            match.source.append(str(network))
        for network in destination:
            match.destination.append(str(network))
        match.protocol = protocol
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_ip6_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.ip6):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_ip6_match(self, forward_rule: int = None):
        completions = []
        if forward_rule is None:
            return completions
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_ip6_match(
        self,
        forward_rule: int,
        forward_rule_ip6_match: int,
        source: list[IPv4Network | IPv6Network] = None,
        destination: list[IPv4Network | IPv6Network] = None,
        protocol: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        if source is not None:
            for network in source:
                match.source.append(str(network))
        if destination is not None:
            for network in destination:
                match.destination.append(str(network))
        if protocol is not None:
            match.protocol = protocol
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip6_match(
        self, forward_rule: int, forward_rule_ip6_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.ip6[forward_rule_ip6_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip6_source(
        self, forward_rule: int, forward_rule_ip6_match: int, source: IPv6Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        match.source.append(str(source))
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip6_source(
        self, forward_rule: int, forward_rule_ip6_match: int, source: IPv6Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        match.source.remove(str(source))
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip6_destination(
        self, forward_rule: int, forward_rule_ip6_match: int, destination: IPv6Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        match.destination.append(str(destination))
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip6_destination(
        self, forward_rule: int, forward_rule_ip6_match: int, destination: IPv6Network
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        match.destination.remove(str(destination))
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ip6_protocol(
        self, forward_rule: int, forward_rule_ip6_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        match.protocol.append(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ip6_protocol(
        self, forward_rule: int, forward_rule_ip6_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ip6[forward_rule_ip6_match]
        match.protocol.remove(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_tcp_match(
        self,
        forward_rule: int,
        source: list[int] = [],
        destination: list[int] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.tcp.add()
        match.source = source
        match.destination = destination
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_tcp_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.tcp):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_tcp_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_tcp_match(
        self,
        forward_rule: int,
        forward_rule_tcp_match: int,
        source: list[int] = None,
        destination: list[int] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.tcp[forward_rule_tcp_match]
        if source is not None:
            match.source = source
        if destination is not None:
            match.destination = destination
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_tcp_match(
        self, forward_rule: int, forward_rule_tcp_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.tcp[forward_rule_tcp_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_tcp_source(
        self, forward_rule: int, forward_rule_tcp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.tcp[forward_rule_tcp_match]
        match.source.append(source)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_tcp_source(
        self, forward_rule: int, forward_rule_tcp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.tcp[forward_rule_tcp_match]
        match.source.remove(source)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_tcp_destination(
        self, forward_rule: int, forward_rule_tcp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.tcp[forward_rule_tcp_match]
        match.destination.append(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_tcp_destination(
        self, forward_rule: int, forward_rule_tcp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.tcp[forward_rule_tcp_match]
        match.destination.remove(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_udp_match(
        self,
        forward_rule: int,
        source: list[int] = [],
        destination: list[int] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.udp.add()
        match.source = source
        match.destination = destination
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_udp_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.udp):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_udp_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_udp_match(
        self,
        forward_rule: int,
        forward_rule_udp_match: int,
        source: list[int] = None,
        destination: list[int] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.udp[forward_rule_udp_match]
        if source is not None:
            match.source = source
        if destination is not None:
            match.destination = destination
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_udp_match(
        self, forward_rule: int, forward_rule_udp_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.udp[forward_rule_udp_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_udp_source(
        self, forward_rule: int, forward_rule_udp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.udp[forward_rule_udp_match]
        match.source.append(source)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_udp_source(
        self, forward_rule: int, forward_rule_udp_match: int, source: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.udp[forward_rule_udp_match]
        match.source.remove(source)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_udp_destination(
        self, forward_rule: int, forward_rule_udp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.udp[forward_rule_udp_match]
        match.destination.append(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_udp_destination(
        self, forward_rule: int, forward_rule_udp_match: int, destination: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.udp[forward_rule_udp_match]
        match.destination.remove(destination)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_icmp_match(
        self,
        forward_rule: int,
        type: list[str] = [],
        code: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp.add()
        match.type = type
        match.code = code
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_icmp_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.icmp):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_icmp_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_icmp_match(
        self,
        forward_rule: int,
        forward_rule_ip_match: int,
        type: list[str] = None,
        code: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp[match]
        if type is not None:
            match.type = type
        if code is not None:
            match.code = code
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_icmp_match(
        self, forward_rule: int, forward_rule_icmp_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.icmp[forward_rule_icmp_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_icmp_type(
        self, forward_rule: int, forward_rule_icmp_match: int, type
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp[forward_rule_icmp_match]
        match.type.append(type)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_icmp_type(
        self, forward_rule: int, forward_rule_icmp_match: int, type
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp[forward_rule_icmp_match]
        match.type.remove(type)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_icmp_code(
        self, forward_rule: int, forward_rule_icmp_match: int, code
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp[forward_rule_icmp_match]
        match.code.append(code)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_icmp_code(
        self, forward_rule: int, forward_rule_icmp_match: int, code
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp[forward_rule_icmp_match]
        match.code.remove(code)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_icmp6_match(
        self,
        forward_rule: int,
        type: list[str] = [],
        code: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp6.add()
        match.type = type
        match.code = code
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_icmp6_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.icmp6):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_icmp6_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_icmp6_match(
        self,
        forward_rule: int,
        forward_rule_icmp6_match: int,
        type: list[str] = None,
        code: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp6[forward_rule_icmp6_match]
        if type is not None:
            match.type = type
        if code is not None:
            match.code = code
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_icmp6_match(
        self, forward_rule: int, forward_rule_icmp6_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.icmp6[forward_rule_icmp6_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_icmp6_type(
        self, forward_rule: int, forward_rule_icmp6_match: int, type: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.input.rule[forward_rule]
        match = rule.icmp6[forward_rule_icmp6_match]
        match.type.append(type)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_icmp6_type(
        self, forward_rule: int, forward_rule_icmp6_match: int, type: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp6[forward_rule_icmp6_match]
        match.type.remove(type)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_icmp6_code(
        self, forward_rule: int, forward_rule_icmp6_match: int, code: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp6[forward_rule_icmp6_match]
        match.code.append(code)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_icmp6_code(
        self, forward_rule: int, forward_rule_icmp6_match: int, code: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.icmp6[forward_rule_icmp6_match]
        match.code.remove(code)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ct_match(
        self, forward_rule: int, state: list[str] = [], negate: bool = False
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ct.add()
        match.state = state
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_ct_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.ct):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_ct_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
        for order, match in enumerate(rule.ct):
            desc = ""
            if match.negate:
                desc += "! "
            if match.state:
                desc += "state=%s " % ",".join(match.state)
            completions.append(Completion(str(order), display="%s %s" % (order, desc)))
        return completions

    async def update_forward_rule_ct_match(
        self,
        forward_rule: int,
        forward_rule_ct_match: int,
        state: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ct[forward_rule_ct_match]
        if state is not None:
            match.state = state
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ct_match(
        self, forward_rule: int, forward_rule_ct_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.ct[forward_rule_ct_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_ct_state(
        self, forward_rule: int, forward_rule_ct_match: int, state: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ct[forward_rule_ct_match]
        match.state.append(state)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_ct_state(
        self, forward_rule: int, forward_rule_ct_match: int, state: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.ct[forward_rule_ct_match]
        match.state.remove(state)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_meta_match(
        self,
        forward_rule: int,
        input_interface: list[str] = [],
        output_interface: list[str] = [],
        protocol: list[str] = [],
        negate: bool = False,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta.add()
        match.input_interface = input_interface
        match.input_interface = output_interface
        match.protocol = protocol
        match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def list_forward_rule_meta_match(self, forward_rule: int):
        s = ""
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        for i, match in enumerate(rule.meta):
            s += f"{i}:\n{textwrap.indent(str(match), '    ')}"
        return s

    async def complete_forward_rule_meta_match(self, forward_rule: int = None):
        completions = []
        config = await self.rpc.request("netfilter/config/get")
        if forward_rule is None or forward_rule >= len(config.forward.rule):
            return completions
        rule = config.forward.rule[forward_rule]
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

    async def update_forward_rule_meta_match(
        self,
        forward_rule: int,
        forward_rule_meta_match: int,
        input_interface: list[str] = None,
        output_interface: list[str] = None,
        protocol: list[str] = None,
        negate: bool = None,
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        if input_interface is not None:
            match.input_interface = input_interface
        if output_interface is not None:
            match.output_interface = output_interface
        if protocol is not None:
            match.protocol = protocol
        if negate is not None:
            match.negate = negate
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_meta_match(
        self, forward_rule: int, forward_rule_meta_match: int
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        del rule.meta[forward_rule_meta_match]
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_meta_input_interface(
        self, forward_rule: int, forward_rule_meta_match: int, interface: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        match.input_interface.append(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_meta_input_interface(
        self, forward_rule: int, forward_rule_meta_match: int, interface: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        match.input_interface.remove(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_meta_output_interface(
        self, forward_rule: int, forward_rule_meta_match: int, interface: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        match.output_interface.append(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_meta_output_interface(
        self, forward_rule: int, forward_rule_meta_match: int, interface: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        match.output_interface.remove(interface)
        await self.rpc.request("netfilter/config/update", config)

    async def add_forward_rule_meta_protocol(
        self, forward_rule: int, forward_rule_meta_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        match.protocol.append(protocol)
        await self.rpc.request("netfilter/config/update", config)

    async def remove_forward_rule_meta_protocol(
        self, forward_rule: int, forward_rule_meta_match: int, protocol: str
    ):
        config = await self.rpc.request("netfilter/config/get")
        rule = config.forward.rule[forward_rule]
        match = rule.meta[forward_rule_meta_match]
        match.protocol.remove(protocol)
        await self.rpc.request("netfilter/config/update", config)
