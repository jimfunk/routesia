from ipaddress import IPv4Address, IPv6Address
import pytest
from socket import AddressFamily
import sys

from routesia.netlink import constants
from routesia.netlink.rtnetlink.route.message import (
    RouteMessage,
    RouteProtocol,
    RouteScope,
    RouteType,
)
from routesia.protoclass.types import Int8, Int32

from tests.buffers import HexBuffer


@pytest.fixture
def rtmsgbuf():
    if sys.byteorder == "little":
        return HexBuffer(
            "02"  # family AF_INET
            "18"  # dst_len 24
            "00"  # src_len 0
            "00"  # tos 0
            "FE"  # table main
            "02"  # protocol kernel
            "00"  # scope global
            "01"  # type unicast
            "08 00"  # len 8
            "0F 00"  # RTA_TABLE
            "FE 00 00 00"  # Main
            "05 00"  # len 5
            "14 00"  # RTA_PREF
            "10"  # 16
            "00 00 00"  # Padding
            "08 00"  # len 8
            "04 00"  # RTA_OIF
            "02 00 00 00"  # ifindex 2
            "08 00"  # len 8
            "01 00"  # RTA_DST
            "0A 01 02 00"  # 10.1.2.0
        )
    else:
        return HexBuffer(
            "02"  # family AF_INET
            "18"  # dst_len 24
            "00"  # src_len 0
            "00"  # tos 0
            "FE"  # table main
            "02"  # protocol kernel
            "00"  # scope global
            "01"  # type unicast
            "08 00"  # len 8
            "0F 00"  # RTA_TABLE
            "00 00 00 FE"  # Main
            "00 05"  # len 5
            "00 14"  # RTA_PREF
            "10"  # 16
            "00 00 00"  # Padding
            "00 08"  # len 8
            "00 04"  # RTA_OIF
            "00 00 00 02"  # ifindex 2
            "00 08"  # len 8
            "00 01"  # RTA_DST
            "0A 01 02 00"  # 10.1.2.0
        )


def test_rtnetlink_message_from_buffer(rtmsgbuf):
    rtmsg = RouteMessage.from_buffer(rtmsgbuf)

    assert rtmsg.rtm_family == AddressFamily.AF_INET
    assert rtmsg.rtm_dst_len == 24
    assert rtmsg.rtm_src_len == 0
    assert rtmsg.rtm_tos == 0
    assert rtmsg.rtm_table == 254
    assert rtmsg.rtm_protocol == 2
    assert rtmsg.rtm_scope == RouteScope.RT_SCOPE_UNIVERSE
    assert rtmsg.rtm_type == RouteType.RTN_UNICAST

    assert len(rtmsg.attributes) == 4

    assert constants.RTA_TABLE in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_TABLE] == [254]

    assert constants.RTA_PREF in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_PREF] == [16]

    assert constants.RTA_OIF in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_OIF] == [2]

    assert constants.RTA_DST in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_DST] == [IPv4Address("10.1.2.0")]


def test_rtnetlink_message_from_buffer_copy(rtmsgbuf):
    rtmsg = RouteMessage.from_buffer(rtmsgbuf)

    assert rtmsg.rtm_family == AddressFamily.AF_INET
    assert rtmsg.rtm_dst_len == 24
    assert rtmsg.rtm_src_len == 0
    assert rtmsg.rtm_tos == 0
    assert rtmsg.rtm_table == 254
    assert rtmsg.rtm_protocol == 2
    assert rtmsg.rtm_protocol == 2
    assert rtmsg.rtm_scope == RouteScope.RT_SCOPE_UNIVERSE
    assert rtmsg.rtm_type == RouteType.RTN_UNICAST

    assert len(rtmsg.attributes) == 4

    assert constants.RTA_TABLE in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_TABLE] == [254]

    assert constants.RTA_PREF in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_PREF] == [16]

    assert constants.RTA_OIF in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_OIF] == [2]

    assert constants.RTA_DST in rtmsg.attributes
    assert rtmsg.attributes[constants.RTA_DST] == [IPv4Address("10.1.2.0")]


def test_encode_rtnetlink_message(rtmsgbuf):
    msg = RouteMessage(
        rtm_family=AddressFamily.AF_INET,
        rtm_dst_len=24,
        rtm_src_len=0,
        rtm_tos=0,
        rtm_table=254,
        rtm_protocol=RouteProtocol.RTPROT_KERNEL,
        rtm_scope=RouteScope.RT_SCOPE_UNIVERSE,
        rtm_type=RouteType.RTN_UNICAST,
    )
    msg.add_attribute(constants.RTA_TABLE, 254)
    msg.add_attribute(constants.RTA_PREF, 16)
    msg.add_attribute(constants.RTA_OIF, 2)
    msg.add_attribute(constants.RTA_DST, IPv4Address("10.1.2.0"))
    assert bytes(msg) == rtmsgbuf
