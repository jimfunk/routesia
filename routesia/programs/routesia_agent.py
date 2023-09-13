#!/usr/bin/python3
#
# routesia -- Routing system
#

import logging
import os
import sys
from systemd.journal import JournalHandler

from routesia.address.provider import AddressProvider
from routesia.config.provider import ConfigProvider
from routesia.dhcp.client.provider import DHCPClientProvider
from routesia.dhcp.server.provider import DHCPServerProvider
from routesia.dns.authoritative.provider import AuthoritativeDNSProvider
from routesia.dns.cache.provider import DNSCacheProvider
from routesia.interface.provider import InterfaceProvider
from routesia.ipam.provider import IPAMProvider
from routesia.mqtt import MQTT
from routesia.netfilter.provider import NetfilterProvider
from routesia.route.provider import RouteProvider
from routesia.rpc import RPC
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.service import Service
from routesia.schema.registry import SchemaRegistry
from routesia.systemd import SystemdProvider


def main():
    if "JOURNAL_STREAM" in os.environ:
        handler = JournalHandler()
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(levelname)s:%(name)s] %(msg)s"))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)
    logger = logging.getLogger("agent")

    for sysctl in (
        "/proc/sys/net/ipv4/ip_forward",
        "/proc/sys/net/ipv6/conf/all/forwarding",
        "/proc/sys/net/ipv6/conf/default/forwarding",
    ):
        with open(sysctl, "w") as f:
            f.write("1")

    service = Service()

    service.add_provider(AddressProvider)
    service.add_provider(AuthoritativeDNSProvider)
    service.add_provider(ConfigProvider)
    service.add_provider(DHCPClientProvider)
    service.add_provider(DHCPServerProvider)
    service.add_provider(DNSCacheProvider)
    service.add_provider(InterfaceProvider)
    service.add_provider(IPAMProvider)
    service.add_provider(IPRouteProvider)
    service.add_provider(MQTT)
    service.add_provider(NetfilterProvider)
    service.add_provider(RouteProvider)
    service.add_provider(RPC, prefix="routesia/agent/rpc")
    service.add_provider(SchemaRegistry)
    service.add_provider(SystemdProvider)

    logger.info("Starting Routesia")

    try:
        service.run()
    except KeyboardInterrupt:
        logger.info("Exiting on keyboard interrupt")
