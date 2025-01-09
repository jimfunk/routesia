from ctypes import (
    addressof,
    c_ubyte,
    cast,
    create_string_buffer,
    memmove,
    POINTER,
    sizeof,
)
from socket import AddressFamily

from routesia.netlink.rtnetlink.base import RTAttribute
from routesia.netlink.message import NetlinkMessage
from routesia.netlink.rtnetlink.route import RouteScope

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
    
    assert msg.nlmsg_len == 24
    assert msg.nlmsg_type == 24
    assert msg.rtm_family == AddressFamily.AF_INET
    assert msg.rtm_dst_len == 24
    assert msg.rtm_src_len == 0
    assert msg.rtm_tos == 0
    assert msg.rtm_table == 254
    assert msg.rtm_protocol == 2
    assert msg.rtm_scope == RouteScope.UNIVERSE

    attributes = list(msg.rtmsg.attributes)

    assert isinstance(attributes[0], RTAttribute)
    assert attributes[0].len == 8
    #assert attributes[0].type ==


"""
recvmsg(
    3,
    {
        msg_name={
            sa_family=AF_NETLINK,
            nl_pid=0,
            nl_groups=00000000
        },
        msg_namelen=12,
        msg_iov=[
            {
                iov_base=[
                    [
                        {
                            nlmsg_len=52,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=0,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_STATIC,
                            rtm_scope=RT_SCOPE_UNIVERSE,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_GATEWAY
                                },
                                inet_addr(
                                    "10.7.41.1"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "enp13s0"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,n
                            lmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_KERNEL,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.7.30.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PREFSRC
                                },
                                inet_addr(
                                    "10.7.30.1"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "br0"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_BIRD,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.7.30.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PRIORITY
                                },
                                32
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "br0"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_KERNEL,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.7.41.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PREFSRC
                                },
                                inet_addr(
                                    "10.7.41.3"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "enp13s0"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_BIRD,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.7.41.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PRIORITY
                                },
                                32
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "enp13s0"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_KERNEL,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.7.42.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PREFSRC
                                },
                                inet_addr(
                                    "10.7.42.3"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "vlan42"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_BIRD,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.7.42.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PRIORITY
                                },
                                32
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "vlan42"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=52,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_STATIC,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },R
                                T_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.72.78.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "wg-hosteria"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,n
                            lmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_KERNEL,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.77.71.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PREFSRC
                                },
                                inet_addr(
                                    "10.77.71.100"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_OIF
                                },
                                if_nametoindex(
                                    "wg-hosteria"
                                )
                            ]
                        ]
                    ],
                    [
                        {
                            nlmsg_len=60,
                            nlmsg_type=RTM_NEWROUTE,
                            nlmsg_flags=NLM_F_MULTI|NLM_F_DUMP_FILTERED,
                            nlmsg_seq=1732095075,
                            nlmsg_pid=753342
                        },
                        {
                            rtm_family=AF_INET,
                            rtm_dst_len=24,
                            rtm_src_len=0,
                            rtm_tos=0,
                            rtm_table=RT_TABLE_MAIN,
                            rtm_protocol=RTPROT_BIRD,
                            rtm_scope=RT_SCOPE_LINK,
                            rtm_type=RTN_UNICAST,
                            rtm_flags=0
                        },
                        [
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_TABLE
                                },
                                RT_TABLE_MAIN
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_DST
                                },
                                inet_addr(
                                    "10.77.71.0"
                                )
                            ],
                            [
                                {
                                    nla_len=8,
                                    nla_type=RTA_PRIORITY
                                },


"""

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
        memmove(
            addressof(msg) + sizeof(MockRTNetlinkMessage) + offset,
            addressof(attr),
            attr.len,
        )
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
