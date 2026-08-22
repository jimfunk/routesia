from enum import IntEnum, IntFlag
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, Union

from socket import AddressFamily

from routesia.netlink import constants
from routesia.protoclass import (
    UInt8Base,
    UInt16Base,
    ProtoClass,
    protoclass,
    VariableLengthData,
    FixedLengthData,
)
from routesia.protoclass.types import (
    UInt8,
    UInt16,
    UInt32,
    Int32,
    IPv4,
    IPv6,
    Bytes,
)
from routesia.netlink.rtnetlink.link.message import InterfaceAttributeType


class RouteProtocol(UInt8Base, IntEnum):
    RTPROT_UNSPEC = constants.RTPROT_UNSPEC
    RTPROT_REDIRECT = constants.RTPROT_REDIRECT
    RTPROT_KERNEL = constants.RTPROT_KERNEL
    RTPROT_BOOT = constants.RTPROT_BOOT
    RTPROT_STATIC = constants.RTPROT_STATIC
    RTPROT_GATED = constants.RTPROT_GATED
    RTPROT_RA = constants.RTPROT_RA
    RTPROT_MRT = constants.RTPROT_MRT
    RTPROT_ZEBRA = constants.RTPROT_ZEBRA
    RTPROT_BIRD = constants.RTPROT_BIRD
    RTPROT_DNROUTED = constants.RTPROT_DNROUTED
    RTPROT_XORP = constants.RTPROT_XORP
    RTPROT_NTK = constants.RTPROT_NTK
    RTPROT_DHCP = constants.RTPROT_DHCP
    RTPROT_MROUTED = constants.RTPROT_MROUTED
    RTPROT_KEEPALIVED = constants.RTPROT_KEEPALIVED
    RTPROT_BABEL = constants.RTPROT_BABEL
    RTPROT_OPENR = constants.RTPROT_OPENR
    RTPROT_BGP = constants.RTPROT_BGP
    RTPROT_ISIS = constants.RTPROT_ISIS
    RTPROT_OSPF = constants.RTPROT_OSPF
    RTPROT_RIP = constants.RTPROT_RIP
    RTPROT_EIGRP = constants.RTPROT_EIGRP
    RTPROT_ROUTESIA = 52  # Currently unassigned


class RouteScope(UInt8Base, IntEnum):
    RT_SCOPE_UNIVERSE = constants.RT_SCOPE_UNIVERSE
    RT_SCOPE_SITE = constants.RT_SCOPE_SITE
    RT_SCOPE_LINK = constants.RT_SCOPE_LINK
    RT_SCOPE_HOST = constants.RT_SCOPE_HOST
    RT_SCOPE_NOWHERE = constants.RT_SCOPE_NOWHERE


class RouteType(UInt8Base, IntEnum):
    RTN_UNSPEC = constants.RTN_UNSPEC
    RTN_UNICAST = constants.RTN_UNICAST
    RTN_LOCAL = constants.RTN_LOCAL
    RTN_BROADCAST = constants.RTN_BROADCAST
    RTN_ANYCAST = constants.RTN_ANYCAST
    RTN_MULTICAST = constants.RTN_MULTICAST
    RTN_BLACKHOLE = constants.RTN_BLACKHOLE
    RTN_UNREACHABLE = constants.RTN_UNREACHABLE
    RTN_PROHIBIT = constants.RTN_PROHIBIT
    RTN_THROW = constants.RTN_THROW
    RTN_NAT = constants.RTN_NAT
    RTN_XRESOLVE = constants.RTN_XRESOLVE


class RouteAttributeType(UInt16Base, IntEnum):
    RTA_UNSPEC = constants.RTA_UNSPEC
    RTA_DST = constants.RTA_DST
    RTA_SRC = constants.RTA_SRC
    RTA_IIF = constants.RTA_IIF
    RTA_OIF = constants.RTA_OIF
    RTA_GATEWAY = constants.RTA_GATEWAY
    RTA_PRIORITY = constants.RTA_PRIORITY
    RTA_PREFSRC = constants.RTA_PREFSRC
    RTA_METRICS = constants.RTA_METRICS
    RTA_MULTIPATH = constants.RTA_MULTIPATH
    RTA_PROTOINFO = constants.RTA_PROTOINFO
    RTA_FLOW = constants.RTA_FLOW
    RTA_CACHEINFO = constants.RTA_CACHEINFO
    RTA_SESSION = constants.RTA_SESSION
    RTA_MP_ALGO = constants.RTA_MP_ALGO
    RTA_TABLE = constants.RTA_TABLE
    RTA_MARK = constants.RTA_MARK
    RTA_MFC_STATS = constants.RTA_MFC_STATS
    RTA_VIA = constants.RTA_VIA
    RTA_NEWDST = constants.RTA_NEWDST
    RTA_PREF = constants.RTA_PREF
    RTA_ENCAP_TYPE = constants.RTA_ENCAP_TYPE
    RTA_ENCAP = constants.RTA_ENCAP
    RTA_EXPIRES = constants.RTA_EXPIRES
    RTA_PAD = constants.RTA_PAD
    RTA_UID = constants.RTA_UID
    RTA_TTL_PROPAGATE = constants.RTA_TTL_PROPAGATE
    RTA_IP_PROTO = constants.RTA_IP_PROTO
    RTA_SPORT = constants.RTA_SPORT
    RTA_DPORT = constants.RTA_DPORT
    RTA_NH_ID = constants.RTA_NH_ID


@protoclass()
class RTNexthopVia():
    family: Annotated[AddressFamily, UInt16]
    addr: Annotated[bytes, VariableLengthData()]

    def __init__(
        self,
        address: IPv4Address | IPv6Address | bytes | None = None,
        family: AddressFamily | None = None,
        **kwargs,
    ):
        if address is not None:
            if isinstance(address, (IPv4Address, IPv6Address)):
                if isinstance(address, IPv4Address):
                    family = AddressFamily.AF_INET
                else:
                    family = AddressFamily.AF_INET6
                kwargs["addr"] = address.packed
            else:
                kwargs["addr"] = address
        if family is not None:
            kwargs["family"] = family
        ProtoClass.__init__(self, **kwargs)

    @property
    def address(self) -> IPv4Address | IPv6Address | bytes:
        if self.family == AddressFamily.AF_INET:
            return IPv4Address(self.addr)
        elif self.family == AddressFamily.AF_INET6:
            return IPv6Address(self.addr)
        return self.addr

    def __str__(self):
        return f"<RTNexthopVia family={self.family.name} address={self.address}>"


@protoclass()
class RTNexthopNestedAttribute():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        bytes, VariableLengthData(length_field="rta_len", length_offset=-4, align=4)
    ]


class RTNexthopFlag(UInt8Base, IntFlag):
    RTNH_F_DEAD = constants.RTNH_F_DEAD
    RTNH_F_PERVASIVE = constants.RTNH_F_PERVASIVE
    RTNH_F_ONLINK = constants.RTNH_F_ONLINK
    RTNH_F_OFFLOAD = constants.RTNH_F_OFFLOAD
    RTNH_F_LINKDOWN = constants.RTNH_F_LINKDOWN
    RTNH_F_UNRESOLVED = constants.RTNH_F_UNRESOLVED
    RTNH_F_TRAP = constants.RTNH_F_TRAP


@protoclass()
class RTNexthop():
    rtnh_len: UInt16
    rtnh_flags: Annotated[RTNexthopFlag, UInt8]
    rtnh_hops: UInt8
    rtnh_ifindex: Int32

    attrs: Annotated[
        list[RTNexthopNestedAttribute],
        VariableLengthData(
            length_field="rtnh_len",
            length_offset=-8,
            item_type=RTNexthopNestedAttribute,
            align=4,
        ),
    ]


@protoclass()
class RTNexthopAttribute():
    nexthops: Annotated[list[RTNexthop], VariableLengthData(item_type=RTNexthop)]


@protoclass()
class RouteAttribute():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[
            UInt32,
            IPv4,
            IPv6,
            RTNexthopAttribute,
            RTNexthopVia,
            Bytes,
        ],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                RouteAttributeType.RTA_DST: IPv4 | IPv6,
                RouteAttributeType.RTA_SRC: IPv4 | IPv6,
                RouteAttributeType.RTA_GATEWAY: IPv4 | IPv6,
                RouteAttributeType.RTA_IIF: UInt32,
                RouteAttributeType.RTA_OIF: UInt32,
                RouteAttributeType.RTA_PREF: UInt8,
                RouteAttributeType.RTA_PREFSRC: IPv4 | IPv6,
                RouteAttributeType.RTA_METRICS: UInt32,
                RouteAttributeType.RTA_TABLE: UInt32,
                RouteAttributeType.RTA_MULTIPATH: RTNexthopAttribute,
                RouteAttributeType.RTA_VIA: RTNexthopVia,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class RouteMessage():
    rtm_family: Annotated[AddressFamily, UInt8]
    rtm_dst_len: UInt8
    rtm_src_len: UInt8
    rtm_tos: UInt8
    rtm_table: UInt8
    rtm_protocol: Annotated[RouteProtocol, UInt8]
    rtm_scope: Annotated[RouteScope, UInt8]
    rtm_type: Annotated[RouteType, UInt8]

    attrs: Annotated[
        list[RouteAttribute], VariableLengthData(item_type=RouteAttribute, align=4)
    ]

    @property
    def dst(self) -> IPv4Address | IPv6Address | None:
        for attr in self.attrs:
            if attr.type == RouteAttributeType.RTA_DST:
                return attr.payload
        return None

    @property
    def gateway(self) -> IPv4Address | IPv6Address | None:
        for attr in self.attrs:
            if attr.type == RouteAttributeType.RTA_GATEWAY:
                return attr.payload
        return None

    @property
    def oif(self) -> int | None:
        for attr in self.attrs:
            if attr.type == RouteAttributeType.RTA_OIF:
                return attr.payload
        return None

    @property
    def attributes(self):
        res = {}
        for attr in self.attrs:
            res.setdefault(attr.type, []).append(attr.payload)
        return res

    def add_attribute(self, attr_type, value):
        attr = RouteAttribute(rta_type=attr_type, payload=value)
        self.attrs.append(attr)

    def __str__(self):
        return f"<RouteMessage family={self.rtm_family.name} table={self.rtm_table} protocol={self.rtm_protocol.name} scope={self.rtm_scope.name} type={self.rtm_type.name}>"
