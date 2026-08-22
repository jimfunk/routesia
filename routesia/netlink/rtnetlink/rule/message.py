from enum import IntEnum, IntFlag
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Union

from socket import AddressFamily

from routesia.netlink import constants
from routesia.protoclass import (
    UInt8Base,
    UInt16Base,
    UInt32Base,
    protoclass,
    VariableLengthData,
)
from routesia.protoclass.types import (
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    Int32,
    IPv4,
    IPv6,
    Bytes,
    NullTerminatedString,
)
from routesia.netlink.rtnetlink.types import EUI


class RuleAttributeType(UInt16Base, IntEnum):
    """
    rtmsg attributes for routing rules
    """
    FRA_UNSPEC = constants.FRA_UNSPEC
    FRA_DST = constants.FRA_DST
    FRA_SRC = constants.FRA_SRC
    FRA_IIFNAME = constants.FRA_IIFNAME
    FRA_GOTO = constants.FRA_GOTO
    FRA_PRIORITY = constants.FRA_PRIORITY
    FRA_FWMARK = constants.FRA_FWMARK
    FRA_FLOW = constants.FRA_FLOW
    FRA_TUN_ID = constants.FRA_TUN_ID
    FRA_SUPPRESS_IFGROUP = constants.FRA_SUPPRESS_IFGROUP
    FRA_SUPPRESS_PREFIXLEN = constants.FRA_SUPPRESS_PREFIXLEN
    FRA_TABLE = constants.FRA_TABLE
    FRA_FWMASK = constants.FRA_FWMASK
    FRA_OIFNAME = constants.FRA_OIFNAME
    FRA_PAD = constants.FRA_PAD
    FRA_L3MDEV = constants.FRA_L3MDEV
    FRA_UID_RANGE = constants.FRA_UID_RANGE
    FRA_PROTOCOL = constants.FRA_PROTOCOL
    FRA_IP_PROTO = constants.FRA_IP_PROTO
    FRA_SPORT_RANGE = constants.FRA_SPORT_RANGE
    FRA_DPORT_RANGE = constants.FRA_DPORT_RANGE


class RuleAction(UInt8Base, IntEnum):
    """
    Routing rule actions
    """
    FR_ACT_UNSPEC = constants.FR_ACT_UNSPEC
    FR_ACT_TO_TBL = constants.FR_ACT_TO_TBL
    FR_ACT_GOTO = constants.FR_ACT_GOTO
    FR_ACT_NOP = constants.FR_ACT_NOP
    FR_ACT_BLACKHOLE = constants.FR_ACT_BLACKHOLE
    FR_ACT_UNREACHABLE = constants.FR_ACT_UNREACHABLE
    FR_ACT_PROHIBIT = constants.FR_ACT_PROHIBIT


class RuleFlag(UInt32Base, IntFlag):
    """
    rtmsg flags for routing rules
    """
    NONE = 0
    RTM_F_NOTIFY = constants.RTM_F_NOTIFY
    RTM_F_CLONED = constants.RTM_F_CLONED
    RTM_F_EQUALIZE = constants.RTM_F_EQUALIZE
    RTM_F_PREFIX = constants.RTM_F_PREFIX
    RTM_F_LOOKUP_TABLE = constants.RTM_F_LOOKUP_TABLE
    RTM_F_FIB_MATCH = constants.RTM_F_FIB_MATCH
    RTM_F_OFFLOAD = constants.RTM_F_OFFLOAD
    RTM_F_TRAP = constants.RTM_F_TRAP


@protoclass()
class RuleUidRange():
    """
    FRA_UID_RANGE attribute payload structure
    """
    start: UInt32
    end: UInt32


@protoclass()
class RulePortRange():
    """
    FRA_SPORT_RANGE / FRA_DPORT_RANGE attribute payload structure
    """
    start: UInt16
    end: UInt16


@protoclass()
class RuleAttribute():
    """
    rtmsg netlink attribute for routing rules
    """
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[
            UInt8,
            UInt16,
            UInt32,
            Int32,
            IPv4,
            IPv6,
            Bytes,
            NullTerminatedString,
            RuleUidRange,
            RulePortRange,
        ],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                RuleAttributeType.FRA_DST: IPv4 | IPv6,
                RuleAttributeType.FRA_SRC: IPv4 | IPv6,
                RuleAttributeType.FRA_IIFNAME: NullTerminatedString,
                RuleAttributeType.FRA_GOTO: UInt32,
                RuleAttributeType.FRA_PRIORITY: UInt32,
                RuleAttributeType.FRA_FWMARK: UInt32,
                RuleAttributeType.FRA_FLOW: UInt32,
                RuleAttributeType.FRA_TUN_ID: UInt64,
                RuleAttributeType.FRA_SUPPRESS_IFGROUP: UInt32,
                RuleAttributeType.FRA_SUPPRESS_PREFIXLEN: UInt32,
                RuleAttributeType.FRA_TABLE: UInt8,
                RuleAttributeType.FRA_FWMASK: UInt32,
                RuleAttributeType.FRA_OIFNAME: NullTerminatedString,
                RuleAttributeType.FRA_L3MDEV: UInt8,
                RuleAttributeType.FRA_UID_RANGE: RuleUidRange,
                RuleAttributeType.FRA_PROTOCOL: UInt8,
                RuleAttributeType.FRA_IP_PROTO: UInt8,
                RuleAttributeType.FRA_SPORT_RANGE: RulePortRange,
                RuleAttributeType.FRA_DPORT_RANGE: RulePortRange,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class RuleMessage():
    """
    rtfibmsg - Routing rule message structure
    
    Used for RTM_NEWRULE, RTM_DELRULE, and RTM_GETRULE messages.
    Implements Linux routing policy rules (ip rule).
    """
    rtm_family: Annotated[AddressFamily, UInt8]
    rtm_dst_len: UInt8
    rtm_src_len: UInt8
    rtm_tos: UInt8
    rtm_table: UInt8
    rtm_action: Annotated[RuleAction, UInt8]
    rtm_flags: Annotated[RuleFlag, UInt32]
    attrs: Annotated[
        list[RuleAttribute],
        VariableLengthData(item_type=RuleAttribute, align=4),
    ]

    @property
    def attributes(self):
        res = {}
        for attr in self.attrs:
            res.setdefault(attr.type, []).append(attr.payload)
        return res

    def add_attribute(self, attr_type, value):
        attr = RuleAttribute(rta_type=attr_type, payload=value)
        self.attrs.append(attr)

    def __str__(self):
        return f"<RuleMessage family={self.rtm_family.name} table={self.rtm_table} action={self.rtm_action.name}>"

    @property
    def dst(self) -> IPv4Address | IPv6Address | None:
        """Get the FRA_DST attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_DST:
                return attr.payload
        return None

    @property
    def src(self) -> IPv4Address | IPv6Address | None:
        """Get the FRA_SRC attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_SRC:
                return attr.payload
        return None

    @property
    def iifname(self) -> str | None:
        """Get the FRA_IIFNAME attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_IIFNAME:
                return attr.payload
        return None

    @property
    def oifname(self) -> str | None:
        """Get the FRA_OIFNAME attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_OIFNAME:
                return attr.payload
        return None

    @property
    def goto(self) -> int | None:
        """Get the FRA_GOTO attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_GOTO:
                return int(attr.payload)
        return None

    @property
    def priority(self) -> int | None:
        """Get the FRA_PRIORITY attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_PRIORITY:
                return int(attr.payload)
        return None

    @property
    def fwmark(self) -> int | None:
        """Get the FRA_FWMARK attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_FWMARK:
                return int(attr.payload)
        return None

    @property
    def flow(self) -> int | None:
        """Get the FRA_FLOW attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_FLOW:
                return int(attr.payload)
        return None

    @property
    def table_id(self) -> int | None:
        """Get the FRA_TABLE attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_TABLE:
                return int(attr.payload)
        return None

    @property
    def fwmask(self) -> int | None:
        """Get the FRA_FWMASK attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_FWMASK:
                return int(attr.payload)
        return None

    @property
    def l3mdev(self) -> int | None:
        """Get the FRA_L3MDEV attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_L3MDEV:
                return int(attr.payload)
        return None

    @property
    def uid_range(self) -> RuleUidRange | None:
        """Get the FRA_UID_RANGE attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_UID_RANGE:
                return attr.payload
        return None

    @property
    def protocol(self) -> int | None:
        """Get the FRA_PROTOCOL attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_PROTOCOL:
                return int(attr.payload)
        return None

    @property
    def ip_proto(self) -> int | None:
        """Get the FRA_IP_PROTO attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_IP_PROTO:
                return int(attr.payload)
        return None

    @property
    def sport_range(self) -> RulePortRange | None:
        """Get the FRA_SPORT_RANGE attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_SPORT_RANGE:
                return attr.payload
        return None

    @property
    def dport_range(self) -> RulePortRange | None:
        """Get the FRA_DPORT_RANGE attribute value"""
        for attr in self.attrs:
            if attr.type == RuleAttributeType.FRA_DPORT_RANGE:
                return attr.payload
        return None
