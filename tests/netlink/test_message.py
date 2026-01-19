import pytest
from socket import AddressFamily

from routesia.netlink.message import NetlinkMessage
from routesia.netlink.rtnetlink.route import RouteScope, RouteMessage

from tests.buffers import HexBuffer


def test_parse_netlink_message():
    buf = HexBuffer(
        "18 00 00 00"  # len 24
        "18 00"  # type RTM_NEWROUTE
        "04 00"  # flags NLM_F_ACK
        "01 00 00 00"  # seq 1
        "15 2a 01 00"  # pid 76309
        "02"  # family AF_INET
        "18"  # dst_len 24
        "00"  # src_len 0
        "00"  # tos 0
        "FE"  # table main
        "02"  # protocol kernel
        "00"  # scope global
        "01"  # type unicast
    )
    msg = NetlinkMessage.from_buffer(buf)

    assert isinstance(msg.payload, RouteMessage)
    assert msg.nlmsg_len == 24
    assert msg.nlmsg_type == 0x18
    assert msg.payload.rtm_family == AddressFamily.AF_INET
    assert msg.payload.rtm_dst_len == 24
    assert msg.payload.rtm_src_len == 0
    assert msg.payload.rtm_tos == 0
    assert msg.payload.rtm_table == 254
    assert msg.payload.rtm_protocol == 2
    assert msg.payload.rtm_scope == RouteScope.RT_SCOPE_UNIVERSE

    assert len(msg.payload.attributes) == 0


def test_parse_netlink_message_short_buf():
    buf = HexBuffer(
        "18"  # nlmsg_len 24
        "00"  # nlmsg_type RTM_NEWROUTE
        "03"  # nlmsg_flags NLM_F_REQUEST | NLM_F_ACK
        "00"  # nlmsg_seq 0
        "00"  # nlmsg_pid 0
    )
    with pytest.raises(ValueError):
        NetlinkMessage.from_buffer(buf)


def test_encode_aligned_payload():
    msg = NetlinkMessage(
        payload=b"\x01\x02\x03\x04",
    )
    assert len(msg) == 20
    assert msg.nlmsg_len == 20
    assert bytes(msg) == HexBuffer(
        "14 00 00 00"  # len 20
        "00 00"  # type
        "00 00"  # flags
        "00 00 00 00"  # seq
        "00 00 00 00"  # pid
        "01 02 03 04"  # payload
    )


def test_encode_unaligned_payload():
    msg = NetlinkMessage(
        payload=b"\x01\x02\x03\x04\x05",
    )
    assert len(msg) == 24
    assert msg.nlmsg_len == 21
    assert bytes(msg) == HexBuffer(
        "15 00 00 00"  # len 21
        "00 00"  # type
        "00 00"  # flags
        "00 00 00 00"  # seq
        "00 00 00 00"  # pid
        "01 02 03 04 05"  # payload
        "00 00 00"  # padding
    )
