"""
tests/interface/test_provider.py
"""

from routesia.interface.provider import InterfaceProvider
from routesia.schema.v1 import interface_pb2


class FakeEntity:
    def __init__(self):
        self.events = []

    async def on_event(self, event):
        self.events.append(event)


async def test_pppoe_events_are_forwarded_to_the_interface():
    entity = FakeEntity()
    provider = InterfaceProvider.__new__(InterfaceProvider)
    provider.interfaces = {"pppoe0": entity}
    event = interface_pb2.PPPoEInterfaceEvent(interface="pppoe0")

    await provider.rpc_pppoe_event(event)

    assert entity.events == [event]


async def test_pppoe_events_for_unknown_interfaces_are_ignored():
    provider = InterfaceProvider.__new__(InterfaceProvider)
    provider.interfaces = {}

    await provider.rpc_pppoe_event(
        interface_pb2.PPPoEInterfaceEvent(interface="pppoe0")
    )
