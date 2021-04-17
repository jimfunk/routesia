"""
tests/address/test_provider.py
"""

from routesia.config import config_pb2


def test_handle_interface_add(address_provider, fake_iproute_provider):
    event = fake_iproute_provider.test_add_interface("enp2s0")
    address_provider.handle_interface_add(event)
    assert "enp2s0" in address_provider.interfaces


def test_handle_interface_remove(address_provider, fake_iproute_provider):
    add_event = fake_iproute_provider.test_add_interface("enp2s0")
    address_provider.handle_interface_add(add_event)
    remove_event = fake_iproute_provider.test_remove_interface("enp2s0")
    address_provider.handle_interface_remove(remove_event)
    assert "enp2s0" not in address_provider.interfaces


def test_handle_address_add(address_provider, fake_iproute_provider):
    address_provider.handle_interface_add(
        fake_iproute_provider.test_add_interface("enp2s0")
    )
    address_provider.handle_address_add(
        fake_iproute_provider.test_add_address("enp2s0", "10.1.2.3/24")
    )
    assert ("enp2s0", "10.1.2.3/24") in address_provider.addresses


def test_on_config_change_add_new_address_no_interface(address_provider, fake_iproute_provider):
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    assert ("enp2s0", "10.1.2.3/24") in address_provider.addresses
    entity = address_provider.addresses[("enp2s0", "10.1.2.3/24")]
    assert entity.ifindex is None
    assert not fake_iproute_provider.iproute.has_address(
        "enp2s0", "10.1.2.3/24")


def test_on_config_change_add_new_address_with_interface(address_provider, fake_iproute_provider):
    address_provider.handle_interface_add(
        fake_iproute_provider.test_add_interface("enp2s0")
    )
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    assert ("enp2s0", "10.1.2.3/24") in address_provider.addresses
    entity = address_provider.addresses[("enp2s0", "10.1.2.3/24")]
    assert entity.ifindex == 1
    assert fake_iproute_provider.iproute.has_address("enp2s0", "10.1.2.3/24")


def test_handle_interface_add_with_address(address_provider, fake_iproute_provider):
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    address_provider.handle_interface_add(
        fake_iproute_provider.test_add_interface("enp2s0")
    )
    assert "enp2s0" in address_provider.interfaces
    assert address_provider.addresses[("enp2s0", "10.1.2.3/24")].ifindex == 1


def test_handle_interface_remove_with_address(address_provider, fake_iproute_provider):
    config = config_pb2.Config()
    address = config.addresses.address.add()
    address.interface = "enp2s0"
    address.ip = "10.1.2.3/24"
    address_provider.on_config_change(config)
    address_provider.handle_interface_add(
        fake_iproute_provider.test_add_interface("enp2s0")
    )
    address_provider.handle_interface_remove(
        fake_iproute_provider.test_remove_interface("enp2s0")
    )
    assert "enp2s0" not in address_provider.interfaces
    assert address_provider.addresses[(
        "enp2s0", "10.1.2.3/24")].ifindex is None
