#!/usr/bin/python3
#
# rcl -- Routesia command line interface
#

import argparse
import asyncio
import logging
import sys

from routesia.address.cli import AddressCLI
from routesia.cli import CLI
from routesia.config.cli import ConfigCLI
from routesia.dhcp.client.cli import DHCPClientCLI
from routesia.dhcp.server.cli import DHCPServerCLI
from routesia.dns.authoritative.cli import DNSAuthoritativeCLI
from routesia.dns.cache.cli import DNSCacheCLI
from routesia.interface.cli import InterfaceCLI
from routesia.ipam.cli import IPAMCLI
from routesia.service import Service
from routesia.mqtt import MQTT
from routesia.netfilter.cli import NetfilterCLI
from routesia.rpcclient import RPCClient
from routesia.route.cli import RouteCLI
from routesia.schema.registry import SchemaRegistry



async def run() -> int:
    parser = argparse.ArgumentParser("rcl", description="Routesia command line interface")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("command", help="Command to run", nargs="*")
    args = parser.parse_args()

    if args.debug:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(levelname)s:%(name)s] %(msg)s"))
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)

    service = Service()
    service.add_provider(AddressCLI)
    service.add_provider(CLI)
    service.add_provider(ConfigCLI)
    service.add_provider(DHCPClientCLI)
    service.add_provider(DHCPServerCLI)
    service.add_provider(DNSAuthoritativeCLI)
    service.add_provider(DNSCacheCLI)
    service.add_provider(InterfaceCLI)
    service.add_provider(IPAMCLI)
    service.add_provider(MQTT)
    service.add_provider(NetfilterCLI)
    service.add_provider(RPCClient, prefix="routesia/agent/rpc")
    service.add_provider(RouteCLI)
    service.add_provider(SchemaRegistry)

    await service.start_background()
    cli = await service.get_provider(CLI)
    ret = await handle(cli, args)
    await service.stop_background()
    return ret


async def handle(cli, args):
    if args.command:
        return await cli.run_command(args.command)

    if not sys.stdin.isatty():
        for line in sys.stdin.readlines():
            ret = await cli.run_command(line)
            if ret:
                return ret
        return 0

    return await cli.run_repl()


def main():
    try:
        sys.exit(asyncio.run(run()))
    except KeyboardInterrupt:
        pass
