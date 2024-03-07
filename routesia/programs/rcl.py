#!/usr/bin/python3
#
# rcl -- Routesia command line interface
#

from routesia.address.cli import AddressCLI
from routesia.cli import CLI
from routesia.config.cli import ConfigCLI
from routesia.dhcp.client.cli import DHCPClientCLI
from routesia.service import Service
from routesia.mqtt import MQTT
from routesia.rpcclient import RPCClient
from routesia.schema.registry import SchemaRegistry


def main():
    service = Service()
    service.add_provider(AddressCLI)
    service.add_provider(CLI)
    service.add_provider(ConfigCLI)
    service.add_provider(DHCPClientCLI)
    service.add_provider(MQTT)
    service.add_provider(RPCClient, prefix="routesia/agent/rpc")
    service.add_provider(SchemaRegistry)

    try:
        service.run()
    except KeyboardInterrupt:
        print("Exiting on keyboard interrupt")
