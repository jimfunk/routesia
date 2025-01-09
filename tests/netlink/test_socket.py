from ctypes import (
    addressof,
    c_ubyte,
    cast,
    create_string_buffer,
    memmove,
    POINTER,
    sizeof,
)

from routesia.netlink.rtnetlink.base import RTAttribute, RTNetlinkMessage
from routesia.netlink.socket import NetlinkMessage

from tests.buffers import HexBuffer


def test_parse_netlink_message(netlink_message):
    buf = HexBuffer(
        "10 00 00 00"  # len 16
        ""
    )



    netlink_message.len = 100
    netlink_message.type = 16
    netlink_message.flags = 0
    netlink_message.seq = 1
    netlink_message.pid = 0

    assert netlink_message.len == 100
    assert netlink_message.type == 16
    assert netlink_message.flags == 0
    assert netlink_message.seq == 1
    assert netlink_message.pid == 0

def test_create_interface_info_message(interface_info_message):
    interface_info_message.family = 2
    interface_info_message.type = 1
    interface_info_message.index = 1
    interface_info_message.flags = 0x1
    interface_info_message.change = 0

    assert interface_info_message.family == 2
    assert interface_info_message.type == 1
    assert interface_info_message.index == 1
    assert interface_info_message.flags == 0x1
    assert interface_info_message.change == 0

def test_create_route_message(route_message):
    route_message.family = 2
    route_message.dst_len = 24
    route_message.src_len = 0
    route_message.tos = 0
    route_message.table = 254
    route_message.protocol = 2
    route_message.scope = 0
    route_message.type = 1

    assert route_message.family == 2
    assert route_message.dst_len == 24
    assert route_message.src_len == 0
    assert route_message.tos == 0
    assert route_message.table == 254
    assert route_message.protocol == 2
    assert route_message.scope == 0
    assert route_message.type == 1

def test_netlink_message_with_interface_info(netlink_message):
    ifinfo = netlink_message.ifinfomsg
    ifinfo.family = 2
    ifinfo.type = 1
    ifinfo.index = 1

    assert netlink_message.ifinfomsg.family == 2
    assert netlink_message.ifinfomsg.type == 1
    assert netlink_message.ifinfomsg.index == 1

def test_netlink_message_with_route_message(netlink_message):
    route = netlink_message.rtmsg
    route.family = 2
    route.dst_len = 24
    route.protocol = 2

    assert netlink_message.rtmsg.family == 2
    assert netlink_message.rtmsg.dst_len == 24
    assert netlink_message.rtmsg.protocol == 2


def create_attribute(type: int, data: bytes) -> RTAttribute:
    attr = RTAttribute()
    attr.len = sizeof(RTAttribute) + len(data)
    attr.type = type
    buffer = create_string_buffer(data)
    attr.data = cast(buffer, POINTER(c_ubyte * len(data))).contents
    return attr


def test_iter_attributes():
    # Create a mock RTNetlinkMessage with attributes
    class MockRTNetlinkMessage(RTNetlinkMessage):
        _fields_ = [("data", c_ubyte * 100)]

    msg = MockRTNetlinkMessage()

    # Create some mock attributes
    attr1 = create_attribute(1, b"test1")
    attr2 = create_attribute(2, b"test2")

    # Copy attributes into the message's data area
    offset = 0
    for attr in [attr1, attr2]:
        memmove(addressof(msg) + sizeof(MockRTNetlinkMessage) + offset,
                       addressof(attr),
                       attr.len)
        offset += RTAttribute.rta_align(attr.len)

    # Set the total length of the message
    total_len = sizeof(NetlinkMessage) + sizeof(MockRTNetlinkMessage) + offset
    nlmsg = cast(addressof(msg) - sizeof(NetlinkMessage), POINTER(NetlinkMessage))[0]
    nlmsg.len = total_len

    # Test iterating over attributes
    attrs = list(msg.iter_attributes())
    assert len(attrs) == 2
    assert attrs[0].type == 1
    assert attrs[1].type == 2
