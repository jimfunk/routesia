#!/usr/bin/python3
#
# rcl -- Routesia command line interface
#

# import argparse
# import sys

# from routesia.address.commands import AddressCommandSet
# from routesia.cli.cli import CLI
# from routesia.config.commands import ConfigCommandSet
# from routesia.dhcp.client.commands import DHCPClientCommandSet
# from routesia.dhcp.server.commands import DHCPServerCommandSet
# from routesia.dns.authoritative.commands import AuthoritativeDNSCommandSet
# from routesia.dns.cache.commands import CacheDNSCommandSet
# from routesia.interface.commands import InterfaceCommandSet
# from routesia.ipam.commands import IPAMCommandSet
# from routesia.netfilter.commands import NetfilterCommandSet
# from routesia.route.commands import RouteCommandSet


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='Interactive command line client for Routesia')
#     parser.add_argument('--command', '-c', help='Run given command and exit')
#     args = parser.parse_args()

#     cli = CLI()
#     cli.register_command_set(AddressCommandSet)
#     cli.register_command_set(AuthoritativeDNSCommandSet)
#     cli.register_command_set(CacheDNSCommandSet)
#     cli.register_command_set(ConfigCommandSet)
#     cli.register_command_set(DHCPClientCommandSet)
#     cli.register_command_set(DHCPServerCommandSet)
#     cli.register_command_set(InterfaceCommandSet)
#     cli.register_command_set(IPAMCommandSet)
#     cli.register_command_set(NetfilterCommandSet)
#     cli.register_command_set(RouteCommandSet)

#     ret = 0

#     if args.command:
#         ret = cli.run_command(args.command)
#     else:
#         cli.run()

#     sys.exit(ret)



from routesia.address.cli import AddressCLI
from routesia.cli import CLI
from routesia.service import Service
from routesia.mqtt import MQTT
from routesia.rpcclient import RPCClient
from routesia.schema.registry import SchemaRegistry


def main():
    service = Service()
    service.add_provider(AddressCLI)
    service.add_provider(CLI)
    service.add_provider(MQTT)
    service.add_provider(RPCClient, prefix="routesia/agent/rpc")
    service.add_provider(SchemaRegistry)

    try:
        service.run()
    except KeyboardInterrupt:
        print("Exiting on keyboard interrupt")
