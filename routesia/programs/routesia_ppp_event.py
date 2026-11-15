#!/usr/bin/python3
#
# routesia-ppp-event -- Routesia PPP link event handler
#

import asyncio
import logging
import os
import sys
from systemd.journal import JournalHandler

from routesia.mqtt import MQTT
from routesia.rpcclient import RPCClient
from routesia.schema.registry import SchemaRegistry
from routesia.schema.v1 import interface_pb2
from routesia.service import Provider, Service


logger = logging.getLogger("ppp-event")


EVENT_TYPES = {
    "ip-up": interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
    "ip-down": interface_pb2.PPPoEInterfaceEvent.IPV4_DOWN,
    "ipv6-up": interface_pb2.PPPoEInterfaceEvent.IPV6_UP,
    "ipv6-down": interface_pb2.PPPoEInterfaceEvent.IPV6_DOWN,
}

IPPARAM_PREFIX = "routesia-pppoe:"


class PPPEvent(Provider):
    def __init__(self, rpc: RPCClient, operation_timeout=5):
        super().__init__()
        self.rpc = rpc
        self.operation_timeout = operation_timeout

    def get_event(self, hook, arguments, environment):
        """
        Build the event from the hook invocation.

        pppd runs its hooks as: interface-name tty-device speed local-address
        remote-address ipparam
        """
        if len(arguments) < 6 or not arguments[5].startswith(IPPARAM_PREFIX):
            return None

        message = interface_pb2.PPPoEInterfaceEvent()
        message.type = EVENT_TYPES[hook]
        message.interface = arguments[0]
        message.local_address = environment.get("IPLOCAL", "")
        message.peer_address = environment.get("IPREMOTE", "")
        message.local_ipv6_address = environment.get("LLLOCAL", "")
        message.peer_ipv6_address = environment.get("LLREMOTE", "")
        message.ac_name = environment.get("ACNAME", "")
        message.remote_mac = environment.get("MACREMOTE", "")
        return message

    async def main(self):
        if len(sys.argv) < 2 or sys.argv[1] not in EVENT_TYPES:
            print("Must be called from a pppd hook", file=sys.stderr)
            return 1

        message = self.get_event(sys.argv[1], sys.argv[2:], os.environ)
        if not message:
            return 0

        try:
            async with asyncio.timeout(self.operation_timeout):
                await self.rpc.wait_connect()
        except TimeoutError:
            logger.error("Timed out connecting to agent")
            return 1

        logger.info("Sending %s event for %s" % (sys.argv[1], message.interface))
        try:
            async with asyncio.timeout(self.operation_timeout):
                await self.rpc.request("interface/pppoe/event", message)
        except TimeoutError:
            logger.error("Timed out sending event")
            return 1

        return 0


async def run() -> int:
    handler = JournalHandler()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    service = Service()
    service.add_provider(PPPEvent)
    service.add_provider(MQTT)
    service.add_provider(RPCClient, prefix="routesia/agent/rpc")
    service.add_provider(SchemaRegistry)

    await service.start_background()
    eventprovider = await service.get_provider(PPPEvent)
    ret = await eventprovider.main()
    await service.stop_background()
    return ret


def main():
    try:
        sys.exit(asyncio.run(run()))
    except KeyboardInterrupt:
        pass
