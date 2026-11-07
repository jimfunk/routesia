from routesia.interface.entities import InterfaceEntity
from routesia.schema.v1 import interface_pb2


class FakeIPRoute:
    def __init__(self):
        self.calls = []

    def link(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeIPRouteProvider:
    def __init__(self):
        self.iproute = FakeIPRoute()


class FakeProvider:
    def __init__(self):
        self.iproute = FakeIPRouteProvider()
        self.running = True


class FakeInterfaceEvent:
    def __init__(self, index, flags, attrs=None):
        self.message = {"index": index, "flags": flags}
        self.attrs = attrs or {}


def test_update_state_applies_link_config_only_on_first_event():
    config = interface_pb2.InterfaceConfig()
    config.name = "eth0"
    config.link.up = True
    provider = FakeProvider()
    entity = InterfaceEntity(provider, "eth0", config)

    down_event = FakeInterfaceEvent(1, 0)
    entity.update_state(down_event)
    entity.update_state(down_event)

    assert provider.iproute.iproute.calls == [
        (("set",), {"index": 1, "state": "up"})
    ]
