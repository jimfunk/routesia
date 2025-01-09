from ctypes import (
    c_uint8,
    c_uint16,
    c_uint32,
    c_uint64,
    Structure,
)
from enum import IntEnum, IntFlag
from socket import AddressFamily

from routesia.interface.eui import EUI
from routesia.netlink import constants
from routesia.netlink.rtnetlink.message import RTNetlinkMessage
from routesia.netlink.types import Int32, UInt8, UInt32


class InterfaceAttributeType(IntEnum):
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
    IFLA_TARGET_NETNSID = constants.IFLA_TARGET_NETNSID
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


class InterfaceType(IntEnum):
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


class InterfaceFlag(IntFlag):
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


class InterfaceStats(Structure):
    _fields_ = [
	    ("rx_packets", c_uint32),
	    ("tx_packets", c_uint32),
	    ("rx_bytes", c_uint32),
	    ("tx_bytes", c_uint32),
	    ("rx_errors", c_uint32),
	    ("tx_errors", c_uint32),
	    ("rx_dropped", c_uint32),
	    ("tx_dropped", c_uint32),
	    ("multicast", c_uint32),
	    ("collisions", c_uint32),
	    ("rx_length_errors", c_uint32),
	    ("rx_over_errors", c_uint32),
	    ("rx_crc_errors", c_uint32),
	    ("rx_frame_errors", c_uint32),
	    ("rx_fifo_errors", c_uint32),
	    ("rx_missed_errors", c_uint32),
	    ("tx_aborted_errors", c_uint32),
	    ("tx_carrier_errors", c_uint32),
	    ("tx_fifo_errors", c_uint32),
	    ("tx_heartbeat_errors", c_uint32),
	    ("tx_window_errors", c_uint32),
	    ("rx_compressed", c_uint32),
	    ("tx_compressed", c_uint32),
	    ("rx_nohandler", c_uint32),
    ]
    rx_packets: int
    tx_packets: int
    rx_bytes: int
    tx_bytes: int
    rx_errors: int
    tx_errors: int
    rx_dropped: int
    tx_dropped: int
    multicast: int
    collisions: int
    rx_length_errors: int
    rx_over_errors: int
    rx_crc_errors: int
    rx_frame_errors: int
    rx_fifo_errors: int
    rx_missed_errors: int
    tx_aborted_errors: int
    tx_carrier_errors: int
    tx_fifo_errors: int
    tx_heartbeat_errors: int
    tx_window_errors: int
    rx_compressed: int
    tx_compressed: int
    rx_nohandler: int


class InterfaceStats64(Structure):
    _fields_ = [
	    ("rx_packets", c_uint64),
	    ("tx_packets", c_uint64),
	    ("rx_bytes", c_uint64),
	    ("tx_bytes", c_uint64),
	    ("rx_errors", c_uint64),
	    ("tx_errors", c_uint64),
	    ("rx_dropped", c_uint64),
	    ("tx_dropped", c_uint64),
	    ("multicast", c_uint64),
	    ("collisions", c_uint64),
	    ("rx_length_errors", c_uint64),
	    ("rx_over_errors", c_uint64),
	    ("rx_crc_errors", c_uint64),
	    ("rx_frame_errors", c_uint64),
	    ("rx_fifo_errors", c_uint64),
	    ("rx_missed_errors", c_uint64),
	    ("tx_aborted_errors", c_uint64),
	    ("tx_carrier_errors", c_uint64),
	    ("tx_fifo_errors", c_uint64),
	    ("tx_heartbeat_errors", c_uint64),
	    ("tx_window_errors", c_uint64),
	    ("rx_compressed", c_uint64),
	    ("tx_compressed", c_uint64),
	    ("rx_nohandler", c_uint64),
	    ("rx_otherhost_dropped", c_uint64),
    ]
    rx_packets: int
    tx_packets: int
    rx_bytes: int
    tx_bytes: int
    rx_errors: int
    tx_errors: int
    rx_dropped: int
    tx_dropped: int
    multicast: int
    collisions: int
    rx_length_errors: int
    rx_over_errors: int
    rx_crc_errors: int
    rx_frame_errors: int
    rx_fifo_errors: int
    rx_missed_errors: int
    tx_aborted_errors: int
    tx_carrier_errors: int
    tx_fifo_errors: int
    tx_heartbeat_errors: int
    tx_window_errors: int
    rx_compressed: int
    tx_compressed: int
    rx_nohandler: int
    rx_otherhost_dropped: int


class InterfaceInfoMessage(RTNetlinkMessage):
    _fields_ = [
        ("_ifi_family", c_uint8),
        ("_ifi_type", c_uint16),
        ("ifi_index", c_uint32),
        ("_ifi_flags", c_uint32),
        ("_ifi_change", c_uint32),
    ]
    ifi_index: int

    _rtattr_type_map = {
        InterfaceAttributeType.IFLA_ADDRESS: EUI,
        InterfaceAttributeType.IFLA_BROADCAST: EUI,
        InterfaceAttributeType.IFLA_IFNAME: str,
        InterfaceAttributeType.IFLA_MTU: UInt32,
        InterfaceAttributeType.IFLA_LINK: Int32,
        InterfaceAttributeType.IFLA_QDISC: str,
        InterfaceAttributeType.IFLA_STATS: InterfaceStats,
        InterfaceAttributeType.IFLA_MASTER: UInt32,
        InterfaceAttributeType.IFLA_TXQLEN: UInt32,
        InterfaceAttributeType.IFLA_WEIGHT: UInt32,
        InterfaceAttributeType.IFLA_OPERSTATE: UInt8,
        InterfaceAttributeType.IFLA_LINKMODE: UInt8,
        InterfaceAttributeType.IFLA_NET_NS_PID: UInt32,
        InterfaceAttributeType.IFLA_IFALIAS: str,
        InterfaceAttributeType.IFLA_NUM_VF: UInt32,
        InterfaceAttributeType.IFLA_STATS64: InterfaceStats64,
        InterfaceAttributeType.IFLA_PERM_ADDRESS: EUI,
    }

    def __init__(
        self,
        ifi_family: AddressFamily = AddressFamily.AF_INET,
        ifi_type: InterfaceType = InterfaceType.ARPHRD_ETHER,
        ifi_index: int = 0,
        ifi_flags: InterfaceFlag = 0,
        ifi_change: InterfaceFlag = 0,
    ):
        super().__init__()
        self.ifi_family = ifi_family
        self.ifi_type = ifi_type
        self.ifi_index = ifi_index
        self.ifi_flags = ifi_flags
        self.ifi_change = ifi_change

    @property
    def ifi_family(self) -> AddressFamily:
        return AddressFamily(self._ifi_family)

    @ifi_family.setter
    def ifi_family(self, value: AddressFamily):
        self._ifi_family = value

    @property
    def ifi_type(self) -> InterfaceType:
        try:
            return InterfaceType(self._ifi_type)
        except ValueError:
            return self._ifi_type

    @ifi_type.setter
    def ifi_type(self, value: InterfaceType | int):
        self._ifi_type = value

    @property
    def ifi_flags(self) -> InterfaceFlag:
        try:
            return InterfaceFlag(self._ifi_flags)
        except ValueError:
            return self._ifi_flags

    @ifi_flags.setter
    def ifi_flags(self, value: InterfaceFlag):
        self._ifi_flags = value

    @property
    def ifi_change(self) -> InterfaceFlag:
        try:
            return InterfaceFlag(self._ifi_change)
        except ValueError:
            return self._ifi_change

    @ifi_change.setter
    def ifi_change(self, value: InterfaceFlag):
        self._ifi_change = value
