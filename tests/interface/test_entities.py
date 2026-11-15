import os
import stat
from types import SimpleNamespace

import pytest

from routesia.config.provider import InvalidConfig
from routesia.interface.entities import (
    INTERFACE_CONFIG_TYPE_ENTITY_MAP,
    INTERFACE_TYPE_ENTITY_MAP,
    InterfaceEntity,
    PPPInterface,
    PPPoEInterface,
)
from routesia.interface.events import PPPoELinkDown, PPPoELinkUp
from routesia.interface.interface_types import ARPHRD_PPP
from routesia.schema.v1 import config_pb2, interface_pb2


class FakeIPRoute:
    def __init__(self):
        self.calls = []

    def link(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeIPRouteProvider:
    def __init__(self):
        self.iproute = FakeIPRoute()


class FakeSystemd:
    def __init__(self):
        self.started = []
        self.stopped = []

    def start_unit(self, unit):
        self.started.append(unit)

    def stop_unit(self, unit):
        self.stopped.append(unit)


class FakeService:
    def __init__(self):
        self.events = []

    def publish_event(self, event):
        self.events.append(event)


class FakeProvider:
    def __init__(self):
        self.iproute = FakeIPRouteProvider()
        self.running = True
        self.systemd = FakeSystemd()
        self.service = FakeService()
        self.config = SimpleNamespace(data=config_pb2.Config())
        self.ifindices = {}

    def get_ifindex(self, ifname):
        return self.ifindices.get(ifname)


class FakeInterfaceEvent:
    def __init__(self, index, flags, attrs=None):
        self.message = {"index": index, "flags": flags}
        self.attrs = attrs or {}


@pytest.fixture
def pppoe(tmp_path):
    return PPPoEInterface(
        FakeProvider(),
        "pppoe0",
        interface_pb2.InterfaceConfig(
            name="pppoe0",
            type=interface_pb2.PPPOE,
            pppoe={"interface": "eth0", "username": "user", "password": "secret"},
        ),
        options_dir=tmp_path,
        pppd_version=(2, 5, 2),
    )


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


def test_ppp_links_are_passive():
    assert INTERFACE_TYPE_ENTITY_MAP[(ARPHRD_PPP, None)] is PPPInterface
    assert INTERFACE_CONFIG_TYPE_ENTITY_MAP[interface_pb2.PPPOE] is PPPoEInterface


def test_ppp_interface_does_not_touch_the_link():
    config = interface_pb2.InterfaceConfig()
    config.name = "ppp0"
    config.link.up = True
    config.link.mtu = 1400
    provider = FakeProvider()
    entity = PPPInterface(provider, "ppp0", config)

    entity.update_state(FakeInterfaceEvent(1, 0))
    entity.apply(new=True)

    assert provider.iproute.iproute.calls == []


def test_pppoe_dependent_interfaces(pppoe):
    assert pppoe.dependent_interfaces == ["eth0"]
    assert PPPoEInterface(FakeProvider(), "pppoe0").dependent_interfaces == []


def test_pppoe_requires_interface():
    entity = PPPoEInterface(
        FakeProvider(),
        "pppoe0",
        interface_pb2.InterfaceConfig(
            name="pppoe0",
            type=interface_pb2.PPPOE,
            pppoe={"username": "user", "password": "secret"},
        ),
    )

    with pytest.raises(InvalidConfig):
        entity.create()


def test_pppoe_requires_username():
    entity = PPPoEInterface(
        FakeProvider(),
        "pppoe0",
        interface_pb2.InterfaceConfig(
            name="pppoe0",
            type=interface_pb2.PPPOE,
            pppoe={"interface": "eth0", "password": "secret"},
        ),
    )

    with pytest.raises(InvalidConfig):
        entity.create()


def test_pppoe_requires_password():
    entity = PPPoEInterface(
        FakeProvider(),
        "pppoe0",
        interface_pb2.InterfaceConfig(
            name="pppoe0",
            type=interface_pb2.PPPOE,
            pppoe={"interface": "eth0", "username": "user"},
        ),
    )

    with pytest.raises(InvalidConfig):
        entity.create()


def test_pppoe_create_waits_for_underlay(pppoe, tmp_path):
    pppoe.create()

    assert pppoe.provider.systemd.started == []
    assert not (tmp_path / "pppoe0.conf").exists()


def test_pppoe_create_starts_session(pppoe, tmp_path):
    pppoe.provider.ifindices["eth0"] = 1

    pppoe.create()

    assert pppoe.provider.systemd.started == ["routesia-pppoe@pppoe0.service"]
    path = tmp_path / "pppoe0.conf"
    assert 'user "user"' in path.read_text()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_pppoe_create_restarts_on_config_change(pppoe):
    pppoe.provider.ifindices["eth0"] = 1
    pppoe.create()

    pppoe.on_config_change(
        interface_pb2.InterfaceConfig(
            name="pppoe0",
            type=interface_pb2.PPPOE,
            pppoe={"interface": "eth0", "username": "user", "password": "other"},
        )
    )

    assert pppoe.provider.systemd.started == [
        "routesia-pppoe@pppoe0.service",
        "routesia-pppoe@pppoe0.service",
    ]


def test_pppoe_applies_when_underlay_appears(pppoe):
    pppoe.create()
    assert pppoe.provider.systemd.started == []

    pppoe.provider.ifindices["eth0"] = 1
    pppoe.on_dependent_interface_add(SimpleNamespace(ifname="eth0"))

    assert pppoe.provider.systemd.started == ["routesia-pppoe@pppoe0.service"]


def test_pppoe_stop_stops_session(pppoe):
    pppoe.provider.ifindices["eth0"] = 1
    pppoe.create()

    pppoe.stop()

    assert pppoe.provider.systemd.stopped == ["routesia-pppoe@pppoe0.service"]


def test_pppoe_config_removal_stops_session(pppoe, tmp_path):
    pppoe.provider.ifindices["eth0"] = 1
    pppoe.create()

    pppoe.on_config_removed()

    assert pppoe.provider.systemd.stopped == ["routesia-pppoe@pppoe0.service"]
    assert not (tmp_path / "pppoe0.conf").exists()


async def test_pppoe_ipv4_up_publishes_link_up_and_records_status(pppoe):
    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
            local_address="192.168.69.20",
            peer_address="192.168.69.0",
            ac_name="pppoe",
            remote_mac="22:25:13:ba:05:42",
        )
    )

    assert pppoe.provider.service.events == [
        PPPoELinkUp(interface="pppoe0", table=0, family=4)
    ]
    assert pppoe.status.local_address == "192.168.69.20"
    assert pppoe.status.peer_address == "192.168.69.0"
    assert pppoe.status.ac_name == "pppoe"
    assert pppoe.status.remote_mac == "22:25:13:ba:05:42"


async def test_pppoe_ipv6_up_publishes_link_up(pppoe):
    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV6_UP,
            local_ipv6_address="fe80::1",
            peer_ipv6_address="fe80::2",
        )
    )

    assert pppoe.provider.service.events == [
        PPPoELinkUp(interface="pppoe0", table=0, family=6)
    ]
    assert pppoe.status.local_ipv6_address == "fe80::1"
    assert pppoe.status.peer_ipv6_address == "fe80::2"


async def test_pppoe_link_up_uses_configured_table(pppoe):
    pppoe.config.pppoe.table = 100

    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
        )
    )

    assert pppoe.provider.service.events == [
        PPPoELinkUp(interface="pppoe0", table=100, family=4)
    ]


async def test_pppoe_ipv4_down_publishes_link_down_and_clears_addresses(pppoe):
    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
            local_address="192.168.69.20",
            peer_address="192.168.69.0",
            ac_name="pppoe",
        )
    )
    pppoe.provider.service.events.clear()

    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_DOWN,
        )
    )

    assert pppoe.provider.service.events == [
        PPPoELinkDown(interface="pppoe0", table=0, family=4)
    ]
    assert pppoe.status.local_address == ""
    assert pppoe.status.peer_address == ""
    assert pppoe.status.ac_name == "pppoe"


async def test_pppoe_ignores_events_without_config():
    entity = PPPoEInterface(FakeProvider(), "pppoe0")

    await entity.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
        )
    )

    assert entity.provider.service.events == []


async def test_pppoe_ipv6_down_publishes_link_down_and_clears_addresses(pppoe):
    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV6_UP,
            local_ipv6_address="fe80::1",
            peer_ipv6_address="fe80::2",
            ac_name="pppoe",
        )
    )
    pppoe.provider.service.events.clear()

    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV6_DOWN,
        )
    )

    assert pppoe.provider.service.events == [
        PPPoELinkDown(interface="pppoe0", table=0, family=6)
    ]
    assert pppoe.status.local_ipv6_address == ""
    assert pppoe.status.peer_ipv6_address == ""
    assert pppoe.status.ac_name == "pppoe"


async def test_pppoe_interface_removal_clears_status(pppoe):
    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
            local_address="192.168.69.20",
        )
    )

    pppoe.on_interface_remove()

    assert pppoe.status.local_address == ""


async def test_pppoe_to_message_includes_session_status(pppoe):
    await pppoe.on_event(
        interface_pb2.PPPoEInterfaceEvent(
            interface="pppoe0",
            type=interface_pb2.PPPoEInterfaceEvent.IPV4_UP,
            local_address="192.168.69.20",
            peer_address="192.168.69.0",
            ac_name="pppoe",
            remote_mac="22:25:13:ba:05:42",
        )
    )
    message = interface_pb2.Interface()

    pppoe.to_message(message)

    assert message.name == "pppoe0"
    assert message.pppoe.local_address == "192.168.69.20"
    assert message.pppoe.peer_address == "192.168.69.0"
    assert message.pppoe.ac_name == "pppoe"
    assert message.pppoe.remote_mac == "22:25:13:ba:05:42"
