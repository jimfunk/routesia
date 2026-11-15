"""
tests/programs/test_ppp_event.py
"""

from routesia.programs.routesia_ppp_event import PPPEvent
from routesia.schema.v1 import interface_pb2


HOOK_ARGUMENTS = [
    "pppoe0",
    "host2",
    "0",
    "192.168.69.20",
    "192.168.69.0",
    "routesia-pppoe:pppoe0",
]

ENVIRONMENT = {
    "IPLOCAL": "192.168.69.20",
    "IPREMOTE": "192.168.69.0",
    "LLLOCAL": "fe80::1",
    "LLREMOTE": "fe80::2",
    "ACNAME": "pppoe",
    "MACREMOTE": "22:25:13:ba:05:42",
}


def test_ipv4_up():
    event = PPPEvent(None).get_event("ip-up", HOOK_ARGUMENTS, ENVIRONMENT)

    assert event.type == interface_pb2.PPPoEInterfaceEvent.IPV4_UP
    assert event.interface == "pppoe0"
    assert event.local_address == "192.168.69.20"
    assert event.peer_address == "192.168.69.0"
    assert event.ac_name == "pppoe"
    assert event.remote_mac == "22:25:13:ba:05:42"


def test_ipv6_up():
    event = PPPEvent(None).get_event("ipv6-up", HOOK_ARGUMENTS, ENVIRONMENT)

    assert event.type == interface_pb2.PPPoEInterfaceEvent.IPV6_UP
    assert event.local_ipv6_address == "fe80::1"
    assert event.peer_ipv6_address == "fe80::2"


def test_down_events():
    assert (
        PPPEvent(None).get_event("ip-down", HOOK_ARGUMENTS, ENVIRONMENT).type
        == interface_pb2.PPPoEInterfaceEvent.IPV4_DOWN
    )
    assert (
        PPPEvent(None).get_event("ipv6-down", HOOK_ARGUMENTS, ENVIRONMENT).type
        == interface_pb2.PPPoEInterfaceEvent.IPV6_DOWN
    )


def test_ignores_links_routesia_does_not_own():
    arguments = ["pppoe0", "host2", "0", "192.168.69.20", "192.168.69.0", "other"]

    assert PPPEvent(None).get_event("ip-up", arguments, ENVIRONMENT) is None
    assert PPPEvent(None).get_event("ip-up", ["pppoe0"], ENVIRONMENT) is None
