"""
tests/interface/test_pppoe.py
"""


import pytest

from routesia.config.provider import InvalidConfig
from routesia.interface import pppoe
from routesia.schema.v1 import interface_pb2


def options(version=(2, 5, 2), **config_fields):
    config = interface_pb2.PPPoEInterfaceConfig(
        **{
            "interface": "eth0",
            "username": "user@example.com",
            "password": "secret",
            **config_fields,
        }
    )
    return pppoe.PPPoEOptions("pppoe0", config, version).generate().splitlines()


def test_defaults():
    result = options()

    assert "plugin pppoe.so" in result
    assert "nic-eth0" in result
    assert "ifname pppoe0" in result
    assert "linkname routesia-pppoe0" in result
    assert "mtu 1492" in result
    assert "mru 1492" in result
    assert "lcp-echo-interval 20" in result
    assert "lcp-echo-failure 3" in result
    assert 'user "user@example.com"' in result
    assert 'password "secret"' in result


def test_routes_are_not_installed_by_pppd():
    result = options()

    assert "nodefaultroute" in result
    assert "nodefaultroute6" in result


def test_ipparam_identifies_the_session():
    assert "ipparam routesia-pppoe:pppoe0" in options()


def test_ipv6_default_route_is_not_left_to_pppd():
    assert "nodefaultroute6" in options()


def test_ppp_24_options():
    result = options(version=(2, 4, 7))

    assert "plugin rp-pppoe.so" in result
    assert "nodefaultroute6" not in result


def test_overrides_distribution_defaults():
    assert "idle 0" in options()


def test_configured_link_parameters():
    result = options(
        mtu=1508,
        mru=1508,
        lcp_echo_interval=10,
        lcp_echo_failure=5,
    )

    assert "mtu 1508" in result
    assert "mru 1508" in result
    assert "lcp-echo-interval 10" in result
    assert "lcp-echo-failure 5" in result


def test_mru_defaults_to_mtu():
    assert "mru 1508" in options(mtu=1508)


def test_quotes_credentials_and_service():
    result = options(username="user name", service="a b", ac="c d")

    assert 'user "user name"' in result
    assert 'rp_pppoe_service "a b"' in result
    assert 'rp_pppoe_ac "c d"' in result


def test_address_mode_any():
    result = options(address_mode=interface_pb2.ANY)

    assert "+ipv6" in result
    assert "noip" not in result
    assert "noipv6" not in result


def test_address_mode_ipv4():
    result = options(address_mode=interface_pb2.IPV4)

    assert "+ipv6" not in result
    assert "noipv6" in result


def test_address_mode_ipv6():
    result = options(address_mode=interface_pb2.IPV6)

    assert "+ipv6" in result
    assert "noip" in result


def test_address_mode_none_is_rejected():
    with pytest.raises(InvalidConfig):
        options(address_mode=interface_pb2.NONE)


def test_ipv6_interface_id():
    ipaddr = interface_pb2.PPPoEInterfaceConfig.IPV4
    persistent = interface_pb2.PPPoEInterfaceConfig.PERSISTENT

    assert "ipv6cp-use-ipaddr" in options(ipv6_interface_id=ipaddr)
    assert "ipv6cp-use-persistent" in options(ipv6_interface_id=persistent)
    assert "ipv6cp-use-ipaddr" not in options()


def test_interface_id_ignored_without_ipv6():
    ipaddr = interface_pb2.PPPoEInterfaceConfig.IPV4

    result = options(address_mode=interface_pb2.IPV4, ipv6_interface_id=ipaddr)

    assert "ipv6cp-use-ipaddr" not in result


def test_detect_pppd_version():
    assert all(isinstance(part, int) for part in pppoe.detect_pppd_version())
