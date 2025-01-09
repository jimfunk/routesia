from ctypes import Structure, c_int, c_uint8, c_ushort, sizeof
from enum import IntEnum, IntFlag
from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily

from routesia.netlink import constants
from routesia.netlink.rtnetlink.attribute import RTAttribute
from routesia.netlink.rtnetlink.message import RTNetlinkMessage
from routesia.netlink.types import Int8, Int32


class RouteProtocol(IntEnum):
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


class RouteScope(IntEnum):
    RT_SCOPE_UNIVERSE = constants.RT_SCOPE_UNIVERSE
    RT_SCOPE_SITE = constants.RT_SCOPE_SITE
    RT_SCOPE_LINK = constants.RT_SCOPE_LINK
    RT_SCOPE_HOST = constants.RT_SCOPE_HOST
    RT_SCOPE_NOWHERE = constants.RT_SCOPE_NOWHERE


class RouteType(IntEnum):
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


class RouteAttributeType(IntEnum):
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


class RTNexthopVia(Structure):
    _fields_ = [
        ("family", c_ushort),
    ]

    def __init__(self, address: IPv4Address | IPv6Address):
        super().__init__()
        self.address = address

    @property
    def address(self) -> IPv4Address | IPv6Address:
        if self.family == AddressFamily.AF_INET:
            return IPv4Address(bytes(self._addr_data))
        else:
            return IPv6Address(bytes(self._addr_data))

    @address.setter
    def address(self, value: IPv4Address | IPv6Address):
        if value.version == 4:
            self.family = AddressFamily.AF_INET
        elif value.version == 6:
            self.family = AddressFamily.AF_INET6
        else:
            raise ValueError("Invalid IP version")
        self._addr_data = value

    def __len__(self):
        return sizeof(self) + len(self._addr_data)

    @classmethod
    def from_buffer(cls, buffer: bytes | bytearray | memoryview) -> "RTNexthopVia":
        obj = type(Structure).from_buffer(cls, buffer)
        addr_data = buffer[sizeof(RTNexthopVia):]
        if obj.family == AddressFamily.AF_INET:
            obj._addr_data = addr_data[:4]
        elif obj.family == AddressFamily.AF_INET6:
            obj._addr_data = IPv6Address(addr_data[:16])
        else:
            raise ValueError("Invalid address family")
        return obj

    @classmethod
    def from_buffer_copy(cls, buffer: bytes | bytearray | memoryview) -> "RTNexthopVia":
        obj = type(Structure).from_buffer_copy(cls, buffer)
        addr_data = bytes(buffer[sizeof(RTNexthopVia):])
        if obj.family == AddressFamily.AF_INET:
            obj._addr_data = addr_data[:4]
        elif obj.family == AddressFamily.AF_INET6:
            obj._addr_data = IPv6Address(addr_data[:16])
        else:
            raise ValueError("Invalid address family")
        return obj

    def __bytes__(self) -> bytes:
        return bytes(memoryview(self)) + self._addr_data


class RTNexthopFlag(IntFlag):
    RTNH_F_DEAD = constants.RTNH_F_DEAD
    RTNH_F_PERVASIVE = constants.RTNH_F_PERVASIVE
    RTNH_F_ONLINK = constants.RTNH_F_ONLINK
    RTNH_F_OFFLOAD = constants.RTNH_F_OFFLOAD
    RTNH_F_LINKDOWN = constants.RTNH_F_LINKDOWN
    RTNH_F_UNRESOLVED = constants.RTNH_F_UNRESOLVED
    RTNH_F_TRAP = constants.RTNH_F_TRAP


class RTNexthopAttribute(RTAttribute):
    _fields_ = [
        ("rtnh_len", c_ushort),
        ("rtnh_flags", c_uint8),
        ("rtnh_hops", c_uint8),
        ("rtnh_ifindex", c_int),
    ]

    def __init__(
        self,
        rtnh_flags: RTNexthopFlag = RTNexthopFlag(0),
        rtnh_hops: int = 0,
        rtnh_ifindex: int = 0,
        rtvias: list[RTNexthopVia] | None = None,
    ):
        self.rtnh_flags = rtnh_flags
        self.rtnh_hops = rtnh_hops
        self.rtnh_ifindex = rtnh_ifindex
        self.rtvias = rtvias or []

    @property
    def rtvias(self) -> list[RTNexthopVia]:
        vias = []
        idx = sizeof(self)
        while idx < self.rtnh_len:
            if self.rta_len < idx + sizeof(RTNexthopVia):
                raise ValueError("Buffer is too small for rtvia")
            via = RTNexthopVia.from_buffer(self.payload, idx)
            vias.append(via)
            idx += len(via)
        return vias

    @rtvias.setter
    def rtvias(self, value: list[RTNexthopVia]):
        self.payload = b"".join(bytes(via) for via in value)


class RouteMessage(RTNetlinkMessage):
    _fields_ = [
        ("_rtm_family", c_uint8),
        ("rtm_dst_len", c_uint8),
        ("rtm_src_len", c_uint8),
        ("rtm_tos", c_uint8),
        ("rtm_table", c_uint8),
        ("_rtm_protocol", c_uint8),
        ("_rtm_scope", c_uint8),
        ("_rtm_type", c_uint8),
    ]

    rtm_dst_len: int
    rtm_src_len: int
    rtm_tos: int
    rtm_table: int

    _rtattr_type_map = {
        RouteAttributeType.RTA_DST: IPv4Address | IPv6Address,
        RouteAttributeType.RTA_SRC: IPv4Address | IPv6Address,
        RouteAttributeType.RTA_IIF: Int32,
        RouteAttributeType.RTA_OIF: Int32,
        RouteAttributeType.RTA_GATEWAY: IPv4Address | IPv6Address,
        RouteAttributeType.RTA_PRIORITY: Int32,
        RouteAttributeType.RTA_PREFSRC: IPv4Address | IPv6Address,
        RouteAttributeType.RTA_METRICS: Int32,
        RouteAttributeType.RTA_MULTIPATH: RTNexthopAttribute,
        RouteAttributeType.RTA_TABLE: Int32,
        RouteAttributeType.RTA_VIA: IPv4Address | IPv6Address,
        RouteAttributeType.RTA_PREF: Int8,
    }

    def __init__(
        self,
        rtm_family: AddressFamily = AddressFamily.AF_INET,
        rtm_dst_len: int = 0,
        rtm_src_len: int = 0,
        rtm_tos: int = 0,
        rtm_table: int = 0,
        rtm_protocol: RouteProtocol | int = RouteProtocol.RTPROT_UNSPEC,
        rtm_scope: RouteScope | int = RouteScope.RT_SCOPE_UNIVERSE,
        rtm_type: RouteType = RouteType.RTN_UNSPEC,
    ):
        super().__init__()
        self.rtm_family = rtm_family
        self.rtm_dst_len = rtm_dst_len
        self.rtm_src_len = rtm_src_len
        self.rtm_tos = rtm_tos
        self.rtm_table = rtm_table
        self.rtm_protocol = rtm_protocol
        self.rtm_scope = rtm_scope
        self.rtm_type = rtm_type

    @property
    def rtm_family(self) -> AddressFamily:
        return AddressFamily(self._rtm_family)

    @rtm_family.setter
    def rtm_family(self, value: AddressFamily):
        self._rtm_family = value

    @property
    def rtm_protocol(self) -> RouteProtocol | int:
        try:
            return RouteProtocol(self._rtm_protocol)
        except ValueError:
            return self._rtm_protocol

    @rtm_protocol.setter
    def rtm_protocol(self, value: RouteProtocol | int):
        self._rtm_protocol = value

    @property
    def rtm_scope(self) -> RouteScope | int:
        try:
            return RouteScope(self._rtm_scope)
        except ValueError:
            return self._rtm_scope

    @rtm_scope.setter
    def rtm_scope(self, value: RouteScope | int):
        self._rtm_scope = value

    @property
    def rtm_type(self) -> RouteType:
        return RouteType(self._rtm_type)

    @rtm_type.setter
    def rtm_type(self, value: RouteType):
        self._rtm_type = value
