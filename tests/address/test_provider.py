"""
tests/address/test_provider.py
"""

from ipaddress import ip_interface

from routesia.rtnetlink.events import (
    AddressAddEvent,
    AddressRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)
from routesia.schema.v1 import config_pb2


async def test_handle_interface_add(ip, service, address_provider):
    ip.add_dummy_link("enp2s0")
    await service.wait_for_event(InterfaceAddEvent, ifname="enp2s0")
    assert "enp2s0" in address_provider.interfaces


async def test_handle_interface_remove(ip, service, address_provider):
    ip.add_dummy_link("enp2s0")
    await service.wait_for_event(InterfaceAddEvent, ifname="enp2s0")
    ip.delete_link("enp2s0")
    await service.wait_for_event(InterfaceRemoveEvent, ifname="enp2s0")
    assert "enp2s0" not in address_provider.interfaces


async def test_handle_address_add(ip, service, address_provider):
    ip.add_dummy_link("enp2s0")
    ip.add_address("10.1.2.3/24", "enp2s0")
    await service.wait_for_event(AddressAddEvent, ip=ip_interface("10.1.2.3/24"))
    assert ("enp2s0", "10.1.2.3/24") in address_provider.addresses


async def test_on_config_change_add_new_address_no_interface(ip, service, address_provider):
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    assert ("enp2s0", "10.1.2.3/24") in address_provider.addresses
    entity = address_provider.addresses[("enp2s0", "10.1.2.3/24")]
    assert entity.ifindex is None


async def test_on_config_change_add_new_address_with_interface(ip, service, address_provider):
    ip.add_dummy_link("enp2s0")
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    assert ("enp2s0", "10.1.2.3/24") in address_provider.addresses
    entity = address_provider.addresses[("enp2s0", "10.1.2.3/24")]
    await service.wait_for_event(AddressAddEvent, ip=ip_interface("10.1.2.3/24"))
    assert entity.ifindex == 2
    assert "10.1.2.3/24" in ip.get_addresses("enp2s0")


async def test_handle_interface_add_with_address(ip, service, address_provider):
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    ip.add_dummy_link("enp2s0")
    await service.wait_for_event(AddressAddEvent, ip=ip_interface("10.1.2.3/24"))
    assert "enp2s0" in address_provider.interfaces
    assert address_provider.addresses[("enp2s0", "10.1.2.3/24")].ifindex == 2


async def test_handle_interface_remove_with_address(ip, service, address_provider):
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    ip.add_dummy_link("enp2s0")
    await service.wait_for_event(InterfaceAddEvent, ifname="enp2s0")
    ip.delete_link("enp2s0")
    await service.wait_for_event(InterfaceRemoveEvent, ifname="enp2s0")
    assert "enp2s0" not in address_provider.interfaces
    assert address_provider.addresses[(
        "enp2s0", "10.1.2.3/24")].ifindex is None
