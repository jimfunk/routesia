"""
routesia/interface/pppoe.py - PPPoE session support
"""

import subprocess

from routesia.config.provider import InvalidConfig
from routesia.schema.v1 import interface_pb2


PPPOE_OPTIONS_DIR = "/run/routesia/pppoe"

DEFAULT_MTU = 1492
DEFAULT_LCP_ECHO_INTERVAL = 20
DEFAULT_LCP_ECHO_FAILURE = 3


def detect_pppd_version():
    "Return the installed pppd version as a tuple of integers"
    # pppd 2.4.x writes the version to stderr
    output = subprocess.check_output(
        ["pppd", "--version"], stderr=subprocess.STDOUT, text=True
    )
    return tuple(int(part) for part in output.split()[-1].split("."))


class PPPoEOptions:
    """
    pppd options for a PPPoE session.

    pppd reads /etc/ppp/options before these options, so anything the
    distribution sets there that would change the behaviour of a managed link
    has to be overridden here. Routes are installed by the route module, not
    by pppd.
    """

    def __init__(self, interface, config, version):
        self.interface = interface
        self.config = config
        self.version = version

    def generate(self):
        config = self.config
        mtu = config.mtu or DEFAULT_MTU

        options = [
            "plugin %s" % ("pppoe.so" if self.version >= (2, 5) else "rp-pppoe.so"),
            "nic-%s" % config.interface,
            "ifname %s" % self.interface,
            "linkname routesia-%s" % self.interface,
            "ipparam routesia-pppoe:%s" % self.interface,
            "noauth",
            "hide-password",
            "persist",
            "maxfail 0",
            "holdoff 5",
            "idle 0",
            "mtu %s" % mtu,
            "mru %s" % (config.mru or mtu),
            "lcp-echo-interval %s"
            % (config.lcp_echo_interval or DEFAULT_LCP_ECHO_INTERVAL),
            "lcp-echo-failure %s"
            % (config.lcp_echo_failure or DEFAULT_LCP_ECHO_FAILURE),
            'user "%s"' % config.username,
            'password "%s"' % config.password,
            "nodefaultroute",
        ]

        if self.version >= (2, 5):
            # pppd would otherwise install its own IPv6 default route
            options.append("nodefaultroute6")

        if config.address_mode == interface_pb2.ANY:
            options.append("+ipv6")
        elif config.address_mode == interface_pb2.IPV4:
            options.append("noipv6")
        elif config.address_mode == interface_pb2.IPV6:
            options.append("noip")
            options.append("+ipv6")
        else:
            raise InvalidConfig(
                "PPPoE address_mode NONE cannot be used because pppd will not "
                "bring up a link without an address family"
            )

        if config.address_mode != interface_pb2.IPV4:
            if config.ipv6_interface_id == interface_pb2.PPPoEInterfaceConfig.IPV4:
                options.append("ipv6cp-use-ipaddr")
            elif (
                config.ipv6_interface_id
                == interface_pb2.PPPoEInterfaceConfig.PERSISTENT
            ):
                options.append("ipv6cp-use-persistent")

        if config.service:
            # rp_pppoe_service is the pre-2.5 spelling. Both versions accept it.
            options.append('rp_pppoe_service "%s"' % config.service)
        if config.ac:
            options.append('rp_pppoe_ac "%s"' % config.ac)

        return "\n".join(options) + "\n"
