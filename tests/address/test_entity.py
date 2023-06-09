"""
tests/address/test_entity.py
"""

import ipaddress
import pytest

from routesia.address import address_pb2
from routesia.address.entity import AddressEntity


class FakeIPRoute:
    def __init__(self):
        self.addresses = []

    def addr(self, cmd, **kwargs):
        if cmd == "add":
            self.addresses.append(kwargs)
        elif cmd == "remove":
            for address in self.addresses:
                if (
                    address["index"] == kwargs["index"] and
                    address["address"] == kwargs["address"] and
                    address["mask"] == kwargs["mask"]
                ):
                    self.addresses.remove(address)
                    break


class FakeIPRouteProvider:
    def __init__(self):
        self.iproute = FakeIPRoute()
        self.rt_proto = 42

    def addr(self, cmd, **kwargs):
        return self.iproute.addr(cmd, **kwargs)


class FakeAddressAddEvent:
    def __init__(self, ifindex, ip, peer=None, scope=0):
        self.ifindex = ifindex
        self.ip = ip
        self.peer = peer
        self.scope = scope


@pytest.fixture
def address_config():
    config = address_pb2.AddressConfig()
    config.interface = "eth0"
    config.ip = "10.1.2.3/24"
    return config


@pytest.fixture
def address_with_config(address_config):
    return AddressEntity("eth0", FakeIPRouteProvider(), config=address_config)


def test_initial_with_config(address_with_config):
    assert address_with_config.state.state == address_pb2.Address.INTERFACE_MISSING
    assert address_with_config.state.address.ip == ""


def test_set_ifindex(address_with_config):
    address_with_config.set_ifindex(2)
    assert address_with_config.ifindex == 2
    assert address_with_config.state.state == address_pb2.Address.ADDRESS_MISSING
    assert address_with_config.iproute.iproute.addresses == [
        {
            "index": 2,
            "address": "10.1.2.3",
            "mask": 24,
            "proto": 42,
        }
    ]


def test_update_state(address_with_config):
    address_with_config.set_ifindex(2)
    address_with_config.update_state(
        FakeAddressAddEvent(2, ipaddress.ip_interface("10.1.2.3/24"))
    )
    assert address_with_config.state.state == address_pb2.Address.PRESENT
    assert address_with_config.state.address.ip == "10.1.2.3/24"
    assert address_with_config.state.address.peer == ""
    assert address_with_config.state.address.scope == 0


def test_update_config(address_with_config):
    address_with_config.set_ifindex(2)
    address_with_config.update_state(
        FakeAddressAddEvent(2, ipaddress.ip_interface("10.1.2.3/24"))
    )
    config = address_pb2.AddressConfig()
    config.interface = "eth0"
    config.ip = "10.2.3.4/27"
    address_with_config.update_config(config)
    assert address_with_config.iproute.iproute.addresses == [
        {
            "index": 2,
            "address": "10.2.3.4",
            "mask": 27,
            "proto": 42,
        }
    ]
