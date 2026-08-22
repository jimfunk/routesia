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
    Int32,
    IPv4,
    IPv6,
    Bytes,
    NullTerminatedString,
)


class AddressAttributeType(UInt16Base, IntEnum):
    """
    ifaddrmsg attribute types
    """
    IFA_UNSPEC = constants.IFA_UNSPEC
    IFA_ADDRESS = constants.IFA_ADDRESS
    IFA_LOCAL = constants.IFA_LOCAL
    IFA_LABEL = constants.IFA_LABEL
    IFA_BROADCAST = constants.IFA_BROADCAST
    IFA_ANYCAST = constants.IFA_ANYCAST
    IFA_CACHEINFO = constants.IFA_CACHEINFO
    IFA_MULTICAST = constants.IFA_MULTICAST
    IFA_FLAGS = constants.IFA_FLAGS


class AddressFlag(UInt32Base, IntFlag):
    """
    ifaddrmsg flags
    """
    NONE = 0
    IFA_F_SECONDARY = constants.IFA_F_SECONDARY
    IFA_F_TEMPORARY = constants.IFA_F_TEMPORARY
    IFA_F_DEPRECATED = constants.IFA_F_DEPRECATED
    IFA_F_TENTATIVE = constants.IFA_F_TENTATIVE
    IFA_F_DADFAILED = constants.IFA_F_DADFAILED
    IFA_F_HOMEADDRESS = constants.IFA_F_HOMEADDRESS
    IFA_F_NODAD = constants.IFA_F_NODAD
    IFA_F_OPTIMISTIC = constants.IFA_F_OPTIMISTIC
    IFA_F_MANAGETEMPADDR = constants.IFA_F_MANAGETEMPADDR
    IFA_F_NOPREFIXROUTE = constants.IFA_F_NOPREFIXROUTE
    IFA_F_MCAUTOJOIN = constants.IFA_F_MCAUTOJOIN
    IFA_F_STABLE_PRIVACY = constants.IFA_F_STABLE_PRIVACY


class AddressScope(UInt8Base, IntEnum):
    """
    ifaddrmsg scope values
    """
    RT_SCOPE_UNIVERSE = constants.RT_SCOPE_UNIVERSE
    RT_SCOPE_SITE = constants.RT_SCOPE_SITE
    RT_SCOPE_LINK = constants.RT_SCOPE_LINK
    RT_SCOPE_HOST = constants.RT_SCOPE_HOST
    RT_SCOPE_NOWHERE = constants.RT_SCOPE_NOWHERE


@protoclass()
class IfAddrCacheInfo():
    """
    IFA_CACHEINFO attribute payload structure
    """
    ifa_prefered: UInt32
    ifa_valid: UInt32
    cstamp: UInt32
    tstamp: UInt32


@protoclass()
class IfAddrAttribute():
    """
    ifaddrmsg netlink attribute
    """
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[
            UInt32,
            IPv4,
            IPv6,
            Bytes,
            IfAddrCacheInfo,
            NullTerminatedString,
        ],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                AddressAttributeType.IFA_ADDRESS: IPv4 | IPv6,
                AddressAttributeType.IFA_LOCAL: IPv4 | IPv6,
                AddressAttributeType.IFA_LABEL: NullTerminatedString,
                AddressAttributeType.IFA_BROADCAST: IPv4 | IPv6,
                AddressAttributeType.IFA_ANYCAST: IPv4 | IPv6,
                AddressAttributeType.IFA_CACHEINFO: IfAddrCacheInfo,
                AddressAttributeType.IFA_MULTICAST: IPv4 | IPv6,
                AddressAttributeType.IFA_FLAGS: UInt32,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class IfAddrMessage():
    """
    ifaddrmsg - Address message structure
    
    Used for RTM_NEWADDR, RTM_DELADDR, and RTM_GETADDR messages.
    """
    ifa_family: Annotated[AddressFamily, UInt8]
    ifa_prefixlen: UInt8
    ifa_flags: Annotated[AddressFlag, UInt8]
    ifa_scope: Annotated[AddressScope, UInt8]
    ifa_index: UInt32
    attrs: Annotated[
        list[IfAddrAttribute],
        VariableLengthData(item_type=IfAddrAttribute, align=4),
    ]

    @property
    def attributes(self):
        res = {}
        for attr in self.attrs:
            res.setdefault(attr.type, []).append(attr.payload)
        return res

    def add_attribute(self, attr_type, value):
        attr = IfAddrAttribute(rta_type=attr_type, payload=value)
        self.attrs.append(attr)

    def __str__(self):
        return f"<IfAddrMessage family={self.ifa_family.name} prefixlen={self.ifa_prefixlen} index={self.ifa_index}>"

    @property
    def address(self) -> IPv4Address | IPv6Address | None:
        """Get the IFA_ADDRESS attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_ADDRESS:
                return attr.payload
        return None

    @property
    def local(self) -> IPv4Address | IPv6Address | None:
        """Get the IFA_LOCAL attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_LOCAL:
                return attr.payload
        return None

    @property
    def broadcast(self) -> IPv4Address | IPv6Address | None:
        """Get the IFA_BROADCAST attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_BROADCAST:
                return attr.payload
        return None

    @property
    def label(self) -> str | None:
        """Get the IFA_LABEL attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_LABEL:
                return attr.payload
        return None

    @property
    def anycast(self) -> IPv4Address | IPv6Address | None:
        """Get the IFA_ANYCAST attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_ANYCAST:
                return attr.payload
        return None

    @property
    def multicast(self) -> IPv4Address | IPv6Address | None:
        """Get the IFA_MULTICAST attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_MULTICAST:
                return attr.payload
        return None

    @property
    def cacheinfo(self) -> IfAddrCacheInfo | None:
        """Get the IFA_CACHEINFO attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_CACHEINFO:
                return attr.payload
        return None

    @property
    def flags_value(self) -> int | None:
        """Get the IFA_FLAGS attribute value"""
        for attr in self.attrs:
            if attr.type == AddressAttributeType.IFA_FLAGS:
                return int(attr.payload)
        return None

    @property
    def flags(self) -> AddressFlag | None:
        """Get the IFA_FLAGS as AddressFlag enum"""
        flags_value = self.flags_value
        if flags_value is not None:
            return AddressFlag(flags_value)
        return None
