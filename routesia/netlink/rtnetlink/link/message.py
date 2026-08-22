from enum import IntEnum, IntFlag

from socket import AddressFamily
from typing import Annotated, Any, Union

from routesia.netlink import constants
from routesia.netlink.rtnetlink.types import EUI
from routesia.protoclass import (
    UInt8Base,
    UInt16Base,
    UInt32Base,
    protoclass,
    VariableLengthData,
    FixedLengthData,
    ProtoClass,
)
from routesia.protoclass.types import (
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    Int32,
    NullTerminatedString,
    Bytes,
)


class InterfaceAttributeType(UInt16Base, IntEnum):
    IFLA_UNSPEC = constants.IFLA_UNSPEC
    IFLA_ADDRESS = constants.IFLA_ADDRESS
    IFLA_BROADCAST = constants.IFLA_BROADCAST
    IFLA_IFNAME = constants.IFLA_IFNAME
    IFLA_MTU = constants.IFLA_MTU
    IFLA_LINK = constants.IFLA_LINK
    IFLA_QDISC = constants.IFLA_QDISC
    IFLA_STATS = constants.IFLA_STATS
    IFLA_COST = constants.IFLA_COST
    IFLA_PRIORITY = constants.IFLA_PRIORITY
    IFLA_MASTER = constants.IFLA_MASTER
    IFLA_WIRELESS = constants.IFLA_WIRELESS
    IFLA_PROTINFO = constants.IFLA_PROTINFO
    IFLA_TXQLEN = constants.IFLA_TXQLEN
    IFLA_MAP = constants.IFLA_MAP
    IFLA_WEIGHT = constants.IFLA_WEIGHT
    IFLA_OPERSTATE = constants.IFLA_OPERSTATE
    IFLA_LINKMODE = constants.IFLA_LINKMODE
    IFLA_LINKINFO = constants.IFLA_LINKINFO
    IFLA_NET_NS_PID = constants.IFLA_NET_NS_PID
    IFLA_IFALIAS = constants.IFLA_IFALIAS
    IFLA_NUM_VF = constants.IFLA_NUM_VF
    IFLA_VFINFO_LIST = constants.IFLA_VFINFO_LIST
    IFLA_STATS64 = constants.IFLA_STATS64
    IFLA_VF_PORTS = constants.IFLA_VF_PORTS
    IFLA_PORT_SELF = constants.IFLA_PORT_SELF
    IFLA_AF_SPEC = constants.IFLA_AF_SPEC
    IFLA_GROUP = constants.IFLA_GROUP
    IFLA_NET_NS_FD = constants.IFLA_NET_NS_FD
    IFLA_EXT_MASK = constants.IFLA_EXT_MASK
    IFLA_PROMISCUITY = constants.IFLA_PROMISCUITY
    IFLA_NUM_TX_QUEUES = constants.IFLA_NUM_TX_QUEUES
    IFLA_NUM_RX_QUEUES = constants.IFLA_NUM_RX_QUEUES
    IFLA_CARRIER = constants.IFLA_CARRIER
    IFLA_PHYS_PORT_ID = constants.IFLA_PHYS_PORT_ID
    IFLA_CARRIER_CHANGES = constants.IFLA_CARRIER_CHANGES
    IFLA_PHYS_SWITCH_ID = constants.IFLA_PHYS_SWITCH_ID
    IFLA_LINK_NETNSID = constants.IFLA_LINK_NETNSID
    IFLA_PHYS_PORT_NAME = constants.IFLA_PHYS_PORT_NAME
    IFLA_PROTO_DOWN = constants.IFLA_PROTO_DOWN
    IFLA_GSO_MAX_SEGS = constants.IFLA_GSO_MAX_SEGS
    IFLA_GSO_MAX_SIZE = constants.IFLA_GSO_MAX_SIZE
    IFLA_PAD = constants.IFLA_PAD
    IFLA_XDP = constants.IFLA_XDP
    IFLA_EVENT = constants.IFLA_EVENT
    IFLA_NEW_NETNSID = constants.IFLA_NEW_NETNSID
    IFLA_IF_NETNSID = constants.IFLA_IF_NETNSID
    IFLA_CARRIER_UP_COUNT = constants.IFLA_CARRIER_UP_COUNT
    IFLA_CARRIER_DOWN_COUNT = constants.IFLA_CARRIER_DOWN_COUNT
    IFLA_NEW_IFINDEX = constants.IFLA_NEW_IFINDEX
    IFLA_MIN_MTU = constants.IFLA_MIN_MTU
    IFLA_MAX_MTU = constants.IFLA_MAX_MTU
    IFLA_PROP_LIST = constants.IFLA_PROP_LIST
    IFLA_ALT_IFNAME = constants.IFLA_ALT_IFNAME
    IFLA_PERM_ADDRESS = constants.IFLA_PERM_ADDRESS
    IFLA_PROTO_DOWN_REASON = constants.IFLA_PROTO_DOWN_REASON
    IFLA_PARENT_DEV_NAME = constants.IFLA_PARENT_DEV_NAME
    IFLA_PARENT_DEV_BUS_NAME = constants.IFLA_PARENT_DEV_BUS_NAME


class ExtMaskFilter(UInt32Base, IntFlag):
    RTEXT_FILTER_VF = constants.RTEXT_FILTER_VF
    RTEXT_FILTER_BRVLAN = constants.RTEXT_FILTER_BRVLAN
    RTEXT_FILTER_BRVLAN_COMPRESSED = constants.RTEXT_FILTER_BRVLAN_COMPRESSED
    RTEXT_FILTER_SKIP_STATS = constants.RTEXT_FILTER_SKIP_STATS
    RTEXT_FILTER_MRP = constants.RTEXT_FILTER_MRP
    RTEXT_FILTER_CFM_CONFIG = constants.RTEXT_FILTER_CFM_CONFIG
    RTEXT_FILTER_CFM_STATUS = constants.RTEXT_FILTER_CFM_STATUS


class InterfaceType(UInt16Base, IntEnum):
    NONE = 0
    ARPHRD_NETROM = constants.ARPHRD_NETROM
    ARPHRD_ETHER = constants.ARPHRD_ETHER
    ARPHRD_EETHER = constants.ARPHRD_EETHER
    ARPHRD_AX25 = constants.ARPHRD_AX25
    ARPHRD_PRONET = constants.ARPHRD_PRONET
    ARPHRD_CHAOS = constants.ARPHRD_CHAOS
    ARPHRD_IEEE802 = constants.ARPHRD_IEEE802
    ARPHRD_ARCNET = constants.ARPHRD_ARCNET
    ARPHRD_APPLETLK = constants.ARPHRD_APPLETLK
    ARPHRD_DLCI = constants.ARPHRD_DLCI
    ARPHRD_ATM = constants.ARPHRD_ATM
    ARPHRD_METRICOM = constants.ARPHRD_METRICOM
    ARPHRD_IEEE1394 = constants.ARPHRD_IEEE1394
    ARPHRD_EUI64 = constants.ARPHRD_EUI64
    ARPHRD_INFINIBAND = constants.ARPHRD_INFINIBAND
    ARPHRD_SLIP = constants.ARPHRD_SLIP
    ARPHRD_CSLIP = constants.ARPHRD_CSLIP
    ARPHRD_SLIP6 = constants.ARPHRD_SLIP6
    ARPHRD_CSLIP6 = constants.ARPHRD_CSLIP6
    ARPHRD_RSRVD = constants.ARPHRD_RSRVD
    ARPHRD_ADAPT = constants.ARPHRD_ADAPT
    ARPHRD_ROSE = constants.ARPHRD_ROSE
    ARPHRD_X25 = constants.ARPHRD_X25
    ARPHRD_HWX25 = constants.ARPHRD_HWX25
    ARPHRD_CAN = constants.ARPHRD_CAN
    ARPHRD_PPP = constants.ARPHRD_PPP
    ARPHRD_CISCO = constants.ARPHRD_CISCO
    ARPHRD_HDLC = constants.ARPHRD_HDLC
    ARPHRD_LAPB = constants.ARPHRD_LAPB
    ARPHRD_DDCMP = constants.ARPHRD_DDCMP
    ARPHRD_RAWHDLC = constants.ARPHRD_RAWHDLC
    ARPHRD_RAWIP = constants.ARPHRD_RAWIP
    ARPHRD_TUNNEL = constants.ARPHRD_TUNNEL
    ARPHRD_TUNNEL6 = constants.ARPHRD_TUNNEL6
    ARPHRD_FRAD = constants.ARPHRD_FRAD
    ARPHRD_SKIP = constants.ARPHRD_SKIP
    ARPHRD_LOOPBACK = constants.ARPHRD_LOOPBACK
    ARPHRD_LOCALTLK = constants.ARPHRD_LOCALTLK
    ARPHRD_FDDI = constants.ARPHRD_FDDI
    ARPHRD_BIF = constants.ARPHRD_BIF
    ARPHRD_SIT = constants.ARPHRD_SIT
    ARPHRD_IPDDP = constants.ARPHRD_IPDDP
    ARPHRD_IPGRE = constants.ARPHRD_IPGRE
    ARPHRD_PIMREG = constants.ARPHRD_PIMREG
    ARPHRD_HIPPI = constants.ARPHRD_HIPPI
    ARPHRD_ASH = constants.ARPHRD_ASH
    ARPHRD_ECONET = constants.ARPHRD_ECONET
    ARPHRD_IRDA = constants.ARPHRD_IRDA
    ARPHRD_FCPP = constants.ARPHRD_FCPP
    ARPHRD_FCAL = constants.ARPHRD_FCAL
    ARPHRD_FCPL = constants.ARPHRD_FCPL
    ARPHRD_FCFABRIC = constants.ARPHRD_FCFABRIC
    ARPHRD_IEEE802_TR = constants.ARPHRD_IEEE802_TR
    ARPHRD_IEEE80211 = constants.ARPHRD_IEEE80211
    ARPHRD_IEEE80211_PRISM = constants.ARPHRD_IEEE80211_PRISM
    ARPHRD_IEEE80211_RADIOTAP = constants.ARPHRD_IEEE80211_RADIOTAP
    ARPHRD_IEEE802154 = constants.ARPHRD_IEEE802154
    ARPHRD_IEEE802154_MONITOR = constants.ARPHRD_IEEE802154_MONITOR
    ARPHRD_PHONET = constants.ARPHRD_PHONET
    ARPHRD_PHONET_PIPE = constants.ARPHRD_PHONET_PIPE
    ARPHRD_CAIF = constants.ARPHRD_CAIF
    ARPHRD_IP6GRE = constants.ARPHRD_IP6GRE
    ARPHRD_NETLINK = constants.ARPHRD_NETLINK
    ARPHRD_6LOWPAN = constants.ARPHRD_6LOWPAN
    ARPHRD_VSOCKMON = constants.ARPHRD_VSOCKMON
    ARPHRD_VOID = constants.ARPHRD_VOID
    ARPHRD_NONE = constants.ARPHRD_NONE


class InterfaceFlag(UInt32Base, IntFlag):
    NONE = 0
    IFF_UP = constants.IFF_UP
    IFF_BROADCAST = constants.IFF_BROADCAST
    IFF_DEBUG = constants.IFF_DEBUG
    IFF_LOOPBACK = constants.IFF_LOOPBACK
    IFF_POINTOPOINT = constants.IFF_POINTOPOINT
    IFF_NOTRAILERS = constants.IFF_NOTRAILERS
    IFF_RUNNING = constants.IFF_RUNNING
    IFF_NOARP = constants.IFF_NOARP
    IFF_PROMISC = constants.IFF_PROMISC
    IFF_ALLMULTI = constants.IFF_ALLMULTI
    IFF_MASTER = constants.IFF_MASTER
    IFF_SLAVE = constants.IFF_SLAVE
    IFF_MULTICAST = constants.IFF_MULTICAST
    IFF_PORTSEL = constants.IFF_PORTSEL
    IFF_AUTOMEDIA = constants.IFF_AUTOMEDIA
    IFF_DYNAMIC = constants.IFF_DYNAMIC
    IFF_LOWER_UP = constants.IFF_LOWER_UP
    IFF_DORMANT = constants.IFF_DORMANT
    IFF_ECHO = constants.IFF_ECHO


class InterfaceOperationalState(UInt8Base, IntEnum):
    IF_OPER_UNKNOWN = constants.IF_OPER_UNKNOWN
    IF_OPER_NOTPRESENT = constants.IF_OPER_NOTPRESENT
    IF_OPER_DOWN = constants.IF_OPER_DOWN
    IF_OPER_LOWERLAYERDOWN = constants.IF_OPER_LOWERLAYERDOWN
    IF_OPER_TESTING = constants.IF_OPER_TESTING
    IF_OPER_DORMANT = constants.IF_OPER_DORMANT
    IF_OPER_UP = constants.IF_OPER_UP


class InterfaceLinkMode(UInt8Base, IntEnum):
    DEFAULT = 0
    DORMANT = 1


class InterfaceCarrier(UInt8Base, IntEnum):
    DOWN = 0
    UP = 1


class InterfaceLinkInfoAttributeType(UInt16Base, IntEnum):
    IFLA_INFO_UNSPEC = constants.IFLA_INFO_UNSPEC
    IFLA_INFO_KIND = constants.IFLA_INFO_KIND
    IFLA_INFO_DATA = constants.IFLA_INFO_DATA
    IFLA_INFO_XSTATS = constants.IFLA_INFO_XSTATS
    IFLA_INFO_SLAVE_KIND = constants.IFLA_INFO_SLAVE_KIND
    IFLA_INFO_SLAVE_DATA = constants.IFLA_INFO_SLAVE_DATA


@protoclass()
class GenericLinkInfoDataAttribute():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[UInt32, UInt16, UInt8, Int32, Bytes],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_map={
                0: Bytes,
                1: UInt32,
            },
            align=4,
        ),
    ]


@protoclass()
class GenericLinkInfoData():
    attrs: Annotated[
        list[GenericLinkInfoDataAttribute],
        VariableLengthData(item_type=GenericLinkInfoDataAttribute, align=4),
    ]


@protoclass()
class InterfaceStats():
    rx_packets: UInt32
    tx_packets: UInt32
    rx_bytes: UInt32
    tx_bytes: UInt32
    rx_errors: UInt32
    tx_errors: UInt32
    rx_dropped: UInt32
    tx_dropped: UInt32
    multicast: UInt32
    collisions: UInt32
    rx_length_errors: UInt32
    rx_over_errors: UInt32
    rx_crc_errors: UInt32
    rx_frame_errors: UInt32
    rx_fifo_errors: UInt32
    rx_missed_errors: UInt32
    tx_aborted_errors: UInt32
    tx_carrier_errors: UInt32
    tx_fifo_errors: UInt32
    tx_heartbeat_errors: UInt32
    tx_window_errors: UInt32
    rx_compressed: UInt32
    tx_compressed: UInt32
    rx_nohandler: UInt32


@protoclass()
class InterfaceStats64():
    rx_packets: UInt64
    tx_packets: UInt64
    rx_bytes: UInt64
    tx_bytes: UInt64
    rx_errors: UInt64
    tx_errors: UInt64
    rx_dropped: UInt64
    tx_dropped: UInt64
    multicast: UInt64
    collisions: UInt64
    rx_length_errors: UInt64
    rx_over_errors: UInt64
    rx_crc_errors: UInt64
    rx_frame_errors: UInt64
    rx_fifo_errors: UInt64
    rx_missed_errors: UInt64
    tx_aborted_errors: UInt64
    tx_carrier_errors: UInt64
    tx_fifo_errors: UInt64
    tx_heartbeat_errors: UInt64
    tx_window_errors: UInt64
    rx_compressed: UInt64
    tx_compressed: UInt64
    rx_nohandler: UInt64
    rx_otherhost_dropped: UInt64


@protoclass()
class InterfaceLinkInfoAttribute():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[Bytes, NullTerminatedString, GenericLinkInfoData],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                InterfaceLinkInfoAttributeType.IFLA_INFO_KIND: NullTerminatedString,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class InterfaceLinkInfo():
    """Container for IFLA_LINKINFO nested attributes."""

    attrs: Annotated[
        list[InterfaceLinkInfoAttribute],
        VariableLengthData(item_type=InterfaceLinkInfoAttribute, align=4),
    ]


@protoclass()
class InterfaceProperty():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[Bytes, NullTerminatedString],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                InterfaceAttributeType.IFLA_ALT_IFNAME: NullTerminatedString,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class InterfacePropertyList():
    attrs: Annotated[
        list[InterfaceProperty],
        VariableLengthData(item_type=InterfaceProperty, align=4),
    ]


@protoclass()
class InterfaceAttribute():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        Union[
            Bytes,
            UInt32,
            EUI,
            NullTerminatedString,
            InterfaceLinkInfo,
            InterfaceStats,
            InterfaceStats64,
        ],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                InterfaceAttributeType.IFLA_IFNAME: NullTerminatedString,
                InterfaceAttributeType.IFLA_ADDRESS: EUI,
                InterfaceAttributeType.IFLA_BROADCAST: EUI,
                InterfaceAttributeType.IFLA_MTU: UInt32,
                InterfaceAttributeType.IFLA_LINK: UInt32,
                InterfaceAttributeType.IFLA_QDISC: NullTerminatedString,
                InterfaceAttributeType.IFLA_TXQLEN: UInt32,
                InterfaceAttributeType.IFLA_OPERSTATE: InterfaceOperationalState,
                InterfaceAttributeType.IFLA_LINKMODE: InterfaceLinkMode,
                InterfaceAttributeType.IFLA_GROUP: UInt32,
                InterfaceAttributeType.IFLA_PROMISCUITY: UInt32,
                InterfaceAttributeType.IFLA_NUM_TX_QUEUES: UInt32,
                InterfaceAttributeType.IFLA_NUM_RX_QUEUES: UInt32,
                InterfaceAttributeType.IFLA_CARRIER: InterfaceCarrier,
                InterfaceAttributeType.IFLA_MASTER: UInt32,
                InterfaceAttributeType.IFLA_CARRIER_UP_COUNT: UInt32,
                InterfaceAttributeType.IFLA_CARRIER_DOWN_COUNT: UInt32,
                InterfaceAttributeType.IFLA_MIN_MTU: UInt32,
                InterfaceAttributeType.IFLA_MAX_MTU: UInt32,
                InterfaceAttributeType.IFLA_LINKINFO: InterfaceLinkInfo,
                InterfaceAttributeType.IFLA_STATS: InterfaceStats,
                InterfaceAttributeType.IFLA_STATS64: InterfaceStats64,
                InterfaceAttributeType.IFLA_NET_NS_PID: UInt32,
                InterfaceAttributeType.IFLA_IFALIAS: NullTerminatedString,
                InterfaceAttributeType.IFLA_NUM_VF: UInt32,
                InterfaceAttributeType.IFLA_PERM_ADDRESS: EUI,
                InterfaceAttributeType.IFLA_PROP_LIST: InterfacePropertyList,
                InterfaceAttributeType.IFLA_PROP_LIST
                | constants.NLA_F_NESTED: InterfacePropertyList,
                InterfaceAttributeType.IFLA_ALT_IFNAME: NullTerminatedString,
                InterfaceAttributeType.IFLA_EXT_MASK: ExtMaskFilter,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class InterfaceInfoMessage():
    ifi_family: Annotated[AddressFamily, UInt8]
    _pad: UInt8
    ifi_type: Annotated[InterfaceType, UInt16]
    ifi_index: Int32
    ifi_flags: Annotated[InterfaceFlag, UInt32]
    ifi_change: Annotated[InterfaceFlag, UInt32]
    attrs: Annotated[
        list[InterfaceAttribute],
        VariableLengthData(item_type=InterfaceAttribute, align=4),
    ]

    @property
    def attributes(self):
        res = {}
        for attr in self.attrs:
            res.setdefault(attr.type, []).append(attr.payload)
        return res

    def add_attribute(self, attr_type, value):
        attr = InterfaceAttribute(rta_type=attr_type, payload=value)
        self.attrs.append(attr)

    def __str__(self):
        iftype = self.ifi_type
        if isinstance(iftype, InterfaceType):
            iftypename = iftype.name
        else:
            iftypename = str(iftype)
        return f"<InterfaceInfoMessage family={self.ifi_family.name} type={iftypename} index={self.ifi_index}>"

    @property
    def ifname(self) -> str:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_IFNAME:
                return attr.payload
        return ""

    @property
    def kind(self) -> str | None:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_LINKINFO:
                linkinfo = attr.payload
                for info_attr in linkinfo.attrs:
                    if info_attr.type == InterfaceLinkInfoAttributeType.IFLA_INFO_KIND:
                        return info_attr.payload
        return None

    @property
    def address(self) -> EUI | None:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_ADDRESS:
                return attr.payload
        return None

    @property
    def master(self) -> int | None:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_MASTER:
                return int(attr.payload)
        return None

    @property
    def operstate(self) -> InterfaceOperationalState | None:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_OPERSTATE:
                return InterfaceOperationalState(attr.payload)
        return None

    @property
    def alias(self) -> str | None:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_IFALIAS:
                return attr.payload
        return None

    @property
    def altnames(self) -> set[str]:
        res = set()
        for attr in self.attrs:
            nla_type = attr.type
            if nla_type == InterfaceAttributeType.IFLA_PROP_LIST:
                for prop in attr.payload.attrs:
                    if prop.type == InterfaceAttributeType.IFLA_ALT_IFNAME:
                        res.add(prop.payload)
            elif nla_type == InterfaceAttributeType.IFLA_ALT_IFNAME:
                res.add(attr.payload)
        return res

    @property
    def perm_address(self) -> EUI | None:
        for attr in self.attrs:
            if attr.type == InterfaceAttributeType.IFLA_PERM_ADDRESS:
                return attr.payload
        return None
