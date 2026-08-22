"""
Tests for rtnetlink neighbor messages (ndmsg).
"""

import pytest
from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily
import sys

from routesia.netlink import constants
from routesia.netlink.rtnetlink.neighbor.message import (
    NeighbourMessage,
    NdAttribute,
    NdCacheInfo,
    NeighborAttributeType,
    NeighborState,
    NeighborFlag,
)
from routesia.interface.eui import EUI
from routesia.protoclass.types import UInt32

from tests.buffers import HexBuffer


class TestNdCacheInfo:
    """Test NdCacheInfo structure."""

    def test_cacheinfo_from_buffer(self):
        """Test parsing NdCacheInfo."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "64 00 00 00"  # ndm_confirmed = 100
                "c8 00 00 00"  # ndm_used = 200
                "2c 01 00 00"  # ndm_updated = 300
                "02 00 00 00"  # ndm_refcnt = 2
            )
        else:
            buf = HexBuffer(
                "00 00 00 64"  # ndm_confirmed = 100
                "00 00 00 c8"  # ndm_used = 200
                "00 00 01 2c"  # ndm_updated = 300
                "00 00 00 02"  # ndm_refcnt = 2
            )
        
        cacheinfo = NdCacheInfo.from_buffer(buf)
        
        assert cacheinfo.ndm_confirmed == 100
        assert cacheinfo.ndm_used == 200
        assert cacheinfo.ndm_updated == 300
        assert cacheinfo.ndm_refcnt == 2

    def test_cacheinfo_to_bytes(self):
        """Test encoding NdCacheInfo."""
        cacheinfo = NdCacheInfo(
            ndm_confirmed=100,
            ndm_used=200,
            ndm_updated=300,
            ndm_refcnt=2,
        )
        
        encoded = bytes(cacheinfo)
        decoded = NdCacheInfo.from_buffer(encoded)
        
        assert decoded.ndm_confirmed == 100
        assert decoded.ndm_used == 200
        assert decoded.ndm_updated == 300
        assert decoded.ndm_refcnt == 2


class TestNdAttribute:
    """Test NdAttribute parsing and encoding."""

    def test_attribute_ipv4_dst(self):
        """Test NDA_DST attribute with IPv4."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = NDA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = NDA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        
        attr = NdAttribute.from_buffer(buf)
        
        assert attr.rta_len == 8
        assert attr.type == NeighborAttributeType.NDA_DST
        assert attr.payload == IPv4Address("10.1.1.1")

    def test_attribute_ipv6_dst(self):
        """Test NDA_DST attribute with IPv6."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "14 00"  # rta_len = 20
                "01 00"  # rta_type = NDA_DST
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        else:
            buf = HexBuffer(
                "00 14"  # rta_len = 20
                "00 01"  # rta_type = NDA_DST
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        
        attr = NdAttribute.from_buffer(buf)
        
        assert attr.rta_len == 20
        assert attr.type == NeighborAttributeType.NDA_DST
        assert attr.payload == IPv6Address("2001:db8::1")

    def test_attribute_lladdr(self):
        """Test NDA_LLADDR attribute (MAC address)."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "0a 00"  # rta_len = 10
                "02 00"  # rta_type = NDA_LLADDR
                "00 11 22 33 44 55"  # MAC address
                "00 00"  # padding
            )
        else:
            buf = HexBuffer(
                "00 0a"  # rta_len = 10
                "00 02"  # rta_type = NDA_LLADDR
                "00 11 22 33 44 55"  # MAC address
                "00 00"  # padding
            )
        
        attr = NdAttribute.from_buffer(buf)
        
        assert attr.type == NeighborAttributeType.NDA_LLADDR
        assert attr.payload == EUI("00:11:22:33:44:55")

    def test_attribute_cacheinfo(self):
        """Test NDA_CACHEINFO attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "14 00"  # rta_len = 20
                "03 00"  # rta_type = NDA_CACHEINFO
                "64 00 00 00"  # ndm_confirmed = 100
                "c8 00 00 00"  # ndm_used = 200
                "2c 01 00 00"  # ndm_updated = 300
                "02 00 00 00"  # ndm_refcnt = 2
            )
        else:
            buf = HexBuffer(
                "00 14"  # rta_len = 20
                "00 03"  # rta_type = NDA_CACHEINFO
                "00 00 00 64"  # ndm_confirmed = 100
                "00 00 00 c8"  # ndm_used = 200
                "00 00 01 2c"  # ndm_updated = 300
                "00 00 00 02"  # ndm_refcnt = 2
            )
        
        attr = NdAttribute.from_buffer(buf)
        
        assert attr.type == NeighborAttributeType.NDA_CACHEINFO
        assert isinstance(attr.payload, NdCacheInfo)
        assert attr.payload.ndm_confirmed == 100

    def test_attribute_vlan(self):
        """Test NDA_VLAN attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "06 00"  # rta_len = 6
                "05 00"  # rta_type = NDA_VLAN
                "0a 00"  # VLAN 10
                "00 00"  # padding
            )
        else:
            buf = HexBuffer(
                "00 06"  # rta_len = 6
                "00 05"  # rta_type = NDA_VLAN
                "00 0a"  # VLAN 10
                "00 00"  # padding
            )
        
        attr = NdAttribute.from_buffer(buf)
        
        assert attr.type == NeighborAttributeType.NDA_VLAN
        assert attr.payload == 10

    def test_attribute_ifindex(self):
        """Test NDA_IFINDEX attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "08 00"  # rta_type = NDA_IFINDEX
                "05 00 00 00"  # ifindex 5
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 08"  # rta_type = NDA_IFINDEX
                "00 00 00 05"  # ifindex 5
            )
        
        attr = NdAttribute.from_buffer(buf)
        
        assert attr.type == NeighborAttributeType.NDA_IFINDEX
        assert attr.payload == 5


class TestNeighbourMessage:
    """Test NeighbourMessage parsing and encoding."""

    def test_ipv4_neighbour_from_buffer(self):
        """Test parsing an IPv4 neighbor entry."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # ndm_family = AF_INET
                "00"  # _pad1
                "00 00"  # ndm_state = NUD_NONE
                "00"  # ndm_flags
                "00"  # ndm_type
                "02 00 00 00"  # ndm_index = 2
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = NDA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        else:
            buf = HexBuffer(
                "02"  # ndm_family = AF_INET
                "00"  # _pad1
                "00 00"  # ndm_state = NUD_NONE
                "00"  # ndm_flags
                "00"  # ndm_type
                "00 00 00 02"  # ndm_index = 2
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = NDA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        
        msg = NeighbourMessage.from_buffer(buf)
        
        assert msg.ndm_family == AddressFamily.AF_INET
        assert msg.ndm_index == 2
        assert msg.ndm_state == NeighborState.NUD_NONE
        assert msg.dst == IPv4Address("10.1.1.1")

    def test_ipv6_neighbour_from_buffer(self):
        """Test parsing an IPv6 neighbor entry."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "0a"  # ndm_family = AF_INET6
                "00"  # _pad1
                "02 00"  # ndm_state = NUD_REACHABLE
                "00"  # ndm_flags
                "00"  # ndm_type
                "03 00 00 00"  # ndm_index = 3
                "14 00"  # rta_len = 20
                "01 00"  # rta_type = NDA_DST
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        else:
            buf = HexBuffer(
                "0a"  # ndm_family = AF_INET6
                "00"  # _pad1
                "00 02"  # ndm_state = NUD_REACHABLE
                "00"  # ndm_flags
                "00"  # ndm_type
                "00 00 00 03"  # ndm_index = 3
                "00 14"  # rta_len = 20
                "00 01"  # rta_type = NDA_DST
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        
        msg = NeighbourMessage.from_buffer(buf)
        
        assert msg.ndm_family == AddressFamily.AF_INET6
        assert msg.ndm_index == 3
        assert msg.ndm_state == NeighborState.NUD_REACHABLE
        assert msg.dst == IPv6Address("2001:db8::1")

    def test_neighbour_with_lladdr(self):
        """Test parsing neighbor with link-layer address."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # ndm_family = AF_INET
                "00"  # _pad1
                "80 00"  # ndm_state = NUD_PERMANENT
                "00"  # ndm_flags
                "00"  # ndm_type
                "02 00 00 00"  # ndm_index = 2
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = NDA_DST
                "0a 01 01 01"  # 10.1.1.1
                "0a 00"  # rta_len = 10
                "02 00"  # rta_type = NDA_LLADDR
                "00 11 22 33 44 55"  # MAC
                "00 00"  # padding
            )
        else:
            buf = HexBuffer(
                "02"  # ndm_family = AF_INET
                "00"  # _pad1
                "00 80"  # ndm_state = NUD_PERMANENT
                "00"  # ndm_flags
                "00"  # ndm_type
                "00 00 00 02"  # ndm_index = 2
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = NDA_DST
                "0a 01 01 01"  # 10.1.1.1
                "00 0a"  # rta_len = 10
                "00 02"  # rta_type = NDA_LLADDR
                "00 11 22 33 44 55"  # MAC
                "00 00"  # padding
            )
        
        msg = NeighbourMessage.from_buffer(buf)
        
        assert msg.ndm_state == NeighborState.NUD_PERMANENT
        assert msg.dst == IPv4Address("10.1.1.1")
        assert msg.lladdr == EUI("00:11:22:33:44:55")
        assert msg.mac == EUI("00:11:22:33:44:55")

    def test_encode_ipv4_neighbour(self):
        """Test encoding an IPv4 neighbor message."""
        msg = NeighbourMessage(
            ndm_family=AddressFamily.AF_INET,
            ndm_index=2,
            ndm_state=NeighborState.NUD_PERMANENT,
        )
        msg.add_attribute(NeighborAttributeType.NDA_DST, IPv4Address("10.1.1.1"))
        msg.add_attribute(NeighborAttributeType.NDA_LLADDR, EUI("00:11:22:33:44:55"))
        
        encoded = bytes(msg)
        decoded = NeighbourMessage.from_buffer(encoded)
        
        assert decoded.ndm_family == AddressFamily.AF_INET
        assert decoded.ndm_index == 2
        assert decoded.ndm_state == NeighborState.NUD_PERMANENT
        assert decoded.dst == IPv4Address("10.1.1.1")
        assert decoded.lladdr == EUI("00:11:22:33:44:55")

    def test_encode_ipv6_neighbour(self):
        """Test encoding an IPv6 neighbor message."""
        msg = NeighbourMessage(
            ndm_family=AddressFamily.AF_INET6,
            ndm_index=3,
            ndm_state=NeighborState.NUD_REACHABLE,
        )
        msg.add_attribute(NeighborAttributeType.NDA_DST, IPv6Address("2001:db8::1"))
        msg.add_attribute(NeighborAttributeType.NDA_LLADDR, EUI("00:11:22:33:44:55"))
        
        encoded = bytes(msg)
        decoded = NeighbourMessage.from_buffer(encoded)
        
        assert decoded.ndm_family == AddressFamily.AF_INET6
        assert decoded.ndm_index == 3
        assert decoded.ndm_state == NeighborState.NUD_REACHABLE
        assert decoded.dst == IPv6Address("2001:db8::1")

    def test_neighbour_properties(self):
        """Test NeighbourMessage property accessors."""
        msg = NeighbourMessage(
            ndm_family=AddressFamily.AF_INET,
            ndm_index=2,
        )
        msg.add_attribute(NeighborAttributeType.NDA_DST, IPv4Address("10.1.1.1"))
        msg.add_attribute(NeighborAttributeType.NDA_LLADDR, EUI("00:11:22:33:44:55"))
        msg.add_attribute(NeighborAttributeType.NDA_VLAN, 100)
        msg.add_attribute(NeighborAttributeType.NDA_IFINDEX, 5)
        
        assert msg.dst == IPv4Address("10.1.1.1")
        assert msg.lladdr == EUI("00:11:22:33:44:55")
        assert msg.mac == EUI("00:11:22:33:44:55")
        assert msg.vlan == 100
        assert msg.ifindex == 5
        assert msg.cacheinfo is None

    def test_neighbour_str(self):
        """Test NeighbourMessage string representation."""
        msg = NeighbourMessage(
            ndm_family=AddressFamily.AF_INET,
            ndm_index=2,
            ndm_state=NeighborState.NUD_REACHABLE,
        )
        
        assert "NeighbourMessage" in str(msg)
        assert "AF_INET" in str(msg)
        assert "2" in str(msg)
        assert "REACHABLE" in str(msg)

    def test_neighbour_various_states(self):
        """Test various neighbor state values."""
        for state in [
            NeighborState.NUD_NONE,
            NeighborState.NUD_INCOMPLETE,
            NeighborState.NUD_REACHABLE,
            NeighborState.NUD_STALE,
            NeighborState.NUD_DELAY,
            NeighborState.NUD_PROBE,
            NeighborState.NUD_FAILED,
            NeighborState.NUD_NOARP,
            NeighborState.NUD_PERMANENT,
        ]:
            msg = NeighbourMessage(
                ndm_family=AddressFamily.AF_INET,
                ndm_index=2,
                ndm_state=state,
            )
            msg.add_attribute(NeighborAttributeType.NDA_DST, IPv4Address("10.1.1.1"))
            
            encoded = bytes(msg)
            decoded = NeighbourMessage.from_buffer(encoded)
            assert decoded.ndm_state == state
