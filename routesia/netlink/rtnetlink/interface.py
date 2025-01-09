from ctypes import (
    c_ubyte,
    c_uint8,
    c_uint16,
    c_uint32,
)
from enum import IntEnum

from routesia.netlink import constants
from routesia.netlink.message import (
    NetlinkMessageType,
)
from routesia.netlink.rtnetlink.base import RTNetlinkMessage


class InterfaceInfoMessage(RTNetlinkMessage):
    _nlmsg_types = (
        NetlinkMessageType.RTM_NEWLINK,
        NetlinkMessageType.RTM_DELLINK,
        NetlinkMessageType.RTM_GETLINK,
        NetlinkMessageType.RTM_SETLINK,
    )
    _fields_ = [
        ("ifi_family", c_uint8),
        ("ifi_type", c_uint16),
        ("ifi_index", c_uint32),
        ("ifi_flags", c_uint32),
        ("ifi_change", c_uint32),
        ("ifi_attrdata", c_ubyte * 0),
    ]
    ifi_family: int
    ifi_type: int
    ifi_index: int
    ifi_flags: int
    ifi_change: int
