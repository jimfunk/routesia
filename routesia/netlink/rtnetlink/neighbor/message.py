from enum import IntEnum, IntFlag
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Union

from socket import AddressFamily

from routesia.netlink import constants
from routesia.interface.eui import EUI
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
)
from routesia.netlink.rtnetlink.types import EUI as EUIType


class NeighborAttributeType(UInt16Base, IntEnum):
    """
    ndmsg netlink attribute types
    """
    NDA_UNSPEC = constants.NDA_UNSPEC
    NDA_DST = constants.NDA_DST
    NDA_LLADDR = constants.NDA_LLADDR
    NDA_CACHEINFO = constants.NDA_CACHEINFO
    NDA_PROBES = constants.NDA_PROBES
    NDA_VLAN = constants.NDA_VLAN
    NDA_PORT = constants.NDA_PORT
    NDA_VNI = constants.NDA_VNI
    NDA_IFINDEX = constants.NDA_IFINDEX
    NDA_MASTER = constants.NDA_MASTER
    NDA_PROTOCOL = constants.NDA_PROTOCOL
    NDA_SRC_VNI = constants.NDA_SRC_VNI


class NeighborState(UInt16Base, IntFlag):
    """
    Neighbor unreachability detection states
    """
    NUD_NONE = constants.NUD_NONE
    NUD_INCOMPLETE = constants.NUD_INCOMPLETE
    NUD_REACHABLE = constants.NUD_REACHABLE
    NUD_STALE = constants.NUD_STALE
    NUD_DELAY = constants.NUD_DELAY
    NUD_PROBE = constants.NUD_PROBE
    NUD_FAILED = constants.NUD_FAILED
    NUD_NOARP = constants.NUD_NOARP
    NUD_PERMANENT = constants.NUD_PERMANENT


class NeighborFlag(UInt8Base, IntFlag):
    """
    ndmsg flags
    """
    NONE = 0
    NTF_USE = constants.NTF_USE
    NTF_SELF = constants.NTF_SELF
    NTF_MASTER = constants.NTF_MASTER
    NTF_PROXY = constants.NTF_PROXY
    NTF_EXT_LEARNED = constants.NTF_EXT_LEARNED
    NTF_OFFLOADED = constants.NTF_OFFLOADED
    NTF_ROUTER = constants.NTF_ROUTER


@protoclass()
class NdCacheInfo():
    """
    NDA_CACHEINFO attribute payload structure
    
    Contains neighbor cache entry statistics.
    """
    ndm_confirmed: UInt32
    ndm_used: UInt32
    ndm_updated: UInt32
    ndm_refcnt: UInt32


@protoclass()
class NdAttribute():
    """
    ndmsg netlink attribute
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
            EUIType,
            NdCacheInfo,
        ],
        VariableLengthData(
            length_field="rta_len",
            length_offset=-4,
            type_field="rta_type",
            type_map={
                NeighborAttributeType.NDA_DST: IPv4 | IPv6,
                NeighborAttributeType.NDA_LLADDR: EUIType,
                NeighborAttributeType.NDA_CACHEINFO: NdCacheInfo,
                NeighborAttributeType.NDA_PROBES: UInt32,
                NeighborAttributeType.NDA_VLAN: UInt16,
                NeighborAttributeType.NDA_PORT: UInt16,
                NeighborAttributeType.NDA_VNI: UInt32,
                NeighborAttributeType.NDA_IFINDEX: UInt32,
                NeighborAttributeType.NDA_MASTER: UInt32,
                NeighborAttributeType.NDA_PROTOCOL: UInt8,
                NeighborAttributeType.NDA_SRC_VNI: UInt32,
            },
            align=4,
        ),
    ]

    @property
    def type(self) -> int:
        return self.rta_type & ~constants.NLA_F_NESTED


@protoclass()
class NeighbourMessage():
    """
    ndmsg - Neighbor message structure
    
    Used for RTM_NEWNEIGH, RTM_DELNEIGH, and RTM_GETNEIGH messages.
    Implements ARP (IPv4) and NDP (IPv6) neighbor table management.
    """
    ndm_family: Annotated[AddressFamily, UInt8]
    _pad1: UInt8
    ndm_state: Annotated[NeighborState, UInt16]
    ndm_flags: Annotated[NeighborFlag, UInt8]
    ndm_type: UInt8
    ndm_index: UInt32
    attrs: Annotated[
        list[NdAttribute],
        VariableLengthData(item_type=NdAttribute, align=4),
    ]

    @property
    def attributes(self):
        res = {}
        for attr in self.attrs:
            res.setdefault(attr.type, []).append(attr.payload)
        return res

    def add_attribute(self, attr_type, value):
        attr = NdAttribute(rta_type=attr_type, payload=value)
        self.attrs.append(attr)

    def __str__(self):
        return f"<NeighbourMessage family={self.ndm_family.name} index={self.ndm_index} state={self.ndm_state.name}>"

    @property
    def dst(self) -> IPv4Address | IPv6Address | None:
        """Get the NDA_DST attribute value (neighbor IP address)"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_DST:
                return attr.payload
        return None

    @property
    def lladdr(self) -> EUI | None:
        """Get the NDA_LLADDR attribute value (link-layer address)"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_LLADDR:
                return attr.payload
        return None

    @property
    def mac(self) -> EUI | None:
        """Get the NDA_LLADDR as EUI (MAC address)"""
        return self.lladdr

    @property
    def cacheinfo(self) -> NdCacheInfo | None:
        """Get the NDA_CACHEINFO attribute value"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_CACHEINFO:
                return attr.payload
        return None

    @property
    def ifindex(self) -> int | None:
        """Get the NDA_IFINDEX attribute value"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_IFINDEX:
                return int(attr.payload)
        return None

    @property
    def vlan(self) -> int | None:
        """Get the NDA_VLAN attribute value"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_VLAN:
                return int(attr.payload)
        return None

    @property
    def port(self) -> int | None:
        """Get the NDA_PORT attribute value (VXLAN port)"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_PORT:
                return int(attr.payload)
        return None

    @property
    def vni(self) -> int | None:
        """Get the NDA_VNI attribute value (VXLAN VNI)"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_VNI:
                return int(attr.payload)
        return None

    @property
    def master(self) -> int | None:
        """Get the NDA_MASTER attribute value (master device index)"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_MASTER:
                return int(attr.payload)
        return None

    @property
    def protocol(self) -> int | None:
        """Get the NDA_PROTOCOL attribute value"""
        for attr in self.attrs:
            if attr.type == NeighborAttributeType.NDA_PROTOCOL:
                return int(attr.payload)
        return None
