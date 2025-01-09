#!/usr/bin/python3
#
# routesia -- Routing system
#

import asyncio
import logging
import os
import sys
from systemd.journal import JournalHandler

from routesia.interface.addressprovider import AddressProvider
from routesia.config.configprovider import ConfigProvider
from routesia.dhcp.dhcpclientprovider import DHCPClientProvider
from routesia.dhcp.dhcpserverprovider import DHCPServerProvider
from routesia.dns.authoritativednsprovider import AuthoritativeDNSProvider
from routesia.dns.dnscacheprovider import DNSCacheProvider
from routesia.interface.interfaceprovider import InterfaceProvider
from routesia.ipam.ipamprovider import IPAMProvider
from routesia.mqtt import MQTT
from routesia.netfilter.netfilterprovider import NetfilterProvider
from routesia.route.routeprovider import RouteProvider
from routesia.rpc import RPC
from routesia.netlink.netlinkprovider import IPRouteProvider
from routesia.service import Service
from routesia.schema.registry import SchemaRegistry
from routesia.systemd import SystemdProvider


async def run():
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
        await service.run()
    except KeyboardInterrupt:
        logger.info("Exiting on keyboard interrupt")

def main():
    try:
        sys.exit(asyncio.run(run()))
    except KeyboardInterrupt:
        pass
