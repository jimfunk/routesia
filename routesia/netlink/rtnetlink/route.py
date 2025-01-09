from ctypes import (
    POINTER,
    Structure,
    addressof,
    c_ubyte,
    c_uint8,
    c_uint16,
    c_uint32,
    cast,
    sizeof,
)
from enum import IntEnum
from typing import Iterator

from routesia.netlink import constants
from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageType,
    NetlinkMessageException,
)
from routesia.netlink.rtnetlink.base import RTNetlinkMessage


class RouteScope(IntEnum):
    UNIVERSE = constants.RT_SCOPE_UNIVERSE
    SITE = constants.RT_SCOPE_SITE
    LINK = constants.RT_SCOPE_LINK
    HOST = constants.RT_SCOPE_HOST
    NOWHERE = constants.RT_SCOPE_NOWHERE


class RouteMessage(RTNetlinkMessage):
    _fields_ = [
        ("rtm_family", c_uint8),
        ("rtm_dst_len", c_uint8),
        ("rtm_src_len", c_uint8),
        ("rtm_tos", c_uint8),
        ("rtm_table", c_uint8),
        ("rtm_protocol", c_uint8),
        ("rtm_scope", c_uint8),
        ("rtm_type", c_uint8),
        ("rtm_attrdata", c_ubyte * 0),
    ]
    rtm_family: int
    rtm_dst_len: int
    rtm_src_len: int
    rtm_tos: int
    rtm_table: int
    rtm_protocol: int
    rtm_scope: int
    rtm_type: int

