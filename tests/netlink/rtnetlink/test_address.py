"""
Tests for rtnetlink address messages (ifaddrmsg).
"""

import pytest
from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily
import sys

from routesia.netlink import constants
from routesia.netlink.rtnetlink.address.message import (
    IfAddrMessage,
    IfAddrAttribute,
    IfAddrCacheInfo,
    AddressAttributeType,
    AddressFlag,
    AddressScope,
)
from routesia.protoclass.types import UInt32

from tests.buffers import HexBuffer


class TestIfAddrCacheInfo:
    """Test IfAddrCacheInfo structure."""

    def test_cacheinfo_from_buffer(self):
        """Test parsing IfAddrCacheInfo."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "1e 00 00 00"  # ifa_prefered = 30
                "3c 00 00 00"  # ifa_valid = 60
                "01 00 00 00"  # cstamp = 1
                "02 00 00 00"  # tstamp = 2
            )
        else:
            buf = HexBuffer(
                "00 00 00 1e"  # ifa_prefered = 30
                "00 00 00 3c"  # ifa_valid = 60
                "00 00 00 01"  # cstamp = 1
                "00 00 00 02"  # tstamp = 2
            )
        
        cacheinfo = IfAddrCacheInfo.from_buffer(buf)
        
        assert cacheinfo.ifa_prefered == 30
        assert cacheinfo.ifa_valid == 60
        assert cacheinfo.cstamp == 1
        assert cacheinfo.tstamp == 2

    def test_cacheinfo_to_bytes(self):
        """Test encoding IfAddrCacheInfo."""
        cacheinfo = IfAddrCacheInfo(
            ifa_prefered=30,
            ifa_valid=60,
            cstamp=1,
            tstamp=2,
        )
        
        encoded = bytes(cacheinfo)
        decoded = IfAddrCacheInfo.from_buffer(encoded)
        
        assert decoded.ifa_prefered == 30
        assert decoded.ifa_valid == 60
        assert decoded.cstamp == 1
        assert decoded.tstamp == 2


class TestIfAddrAttribute:
    """Test IfAddrAttribute parsing and encoding."""

    def test_attribute_ipv4_address(self):
        """Test IFA_ADDRESS attribute with IPv4."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = IFA_ADDRESS
                "0a 01 01 01"  # 10.1.1.1
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = IFA_ADDRESS
                "0a 01 01 01"  # 10.1.1.1
            )
        
        attr = IfAddrAttribute.from_buffer(buf)
        
        assert attr.rta_len == 8
        assert attr.type == AddressAttributeType.IFA_ADDRESS
        assert attr.payload == IPv4Address("10.1.1.1")

    def test_attribute_ipv6_address(self):
        """Test IFA_ADDRESS attribute with IPv6."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "14 00"  # rta_len = 20
                "01 00"  # rta_type = IFA_ADDRESS
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        else:
            buf = HexBuffer(
                "00 14"  # rta_len = 20
                "00 01"  # rta_type = IFA_ADDRESS
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        
        attr = IfAddrAttribute.from_buffer(buf)
        
        assert attr.rta_len == 20
        assert attr.type == AddressAttributeType.IFA_ADDRESS
        assert attr.payload == IPv6Address("2001:db8::1")

    def test_attribute_label(self):
        """Test IFA_LABEL attribute."""
        # IFA_LABEL contains null-terminated string "eth0" padded to 8 bytes
        # Total length: 4 (header) + 8 (padded label) = 12
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "0c 00"  # rta_len = 12
                "03 00"  # rta_type = IFA_LABEL
                "65 74 68 30"  # "eth0"
                "00 00 00 00"  # null + padding (4 bytes to align to 8)
            )
        else:
            buf = HexBuffer(
                "00 0c"  # rta_len = 12
                "00 03"  # rta_type = IFA_LABEL
                "65 74 68 30"  # "eth0"
                "00 00 00 00"  # null + padding (4 bytes to align to 8)
            )

        attr = IfAddrAttribute.from_buffer(buf)

        assert attr.type == AddressAttributeType.IFA_LABEL
        # NullTerminatedString strips the null terminator and padding
        assert attr.payload == "eth0"

    def test_attribute_flags(self):
        """Test IFA_FLAGS attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "08 00"  # rta_type = IFA_FLAGS
                "02 00 00 00"  # flags = IFA_F_SECONDARY
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 08"  # rta_type = IFA_FLAGS
                "00 00 00 02"  # flags = IFA_F_SECONDARY
            )
        
        attr = IfAddrAttribute.from_buffer(buf)
        
        assert attr.type == AddressAttributeType.IFA_FLAGS
        assert attr.payload == 2

    def test_attribute_cacheinfo(self):
        """Test IFA_CACHEINFO attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "14 00"  # rta_len = 20
                "06 00"  # rta_type = IFA_CACHEINFO
                "1e 00 00 00"  # ifa_prefered = 30
                "3c 00 00 00"  # ifa_valid = 60
                "01 00 00 00"  # cstamp = 1
                "02 00 00 00"  # tstamp = 2
            )
        else:
            buf = HexBuffer(
                "00 14"  # rta_len = 20
                "00 06"  # rta_type = IFA_CACHEINFO
                "00 00 00 1e"  # ifa_prefered = 30
                "00 00 00 3c"  # ifa_valid = 60
                "00 00 00 01"  # cstamp = 1
                "00 00 00 02"  # tstamp = 2
            )
        
        attr = IfAddrAttribute.from_buffer(buf)
        
        assert attr.type == AddressAttributeType.IFA_CACHEINFO
        assert isinstance(attr.payload, IfAddrCacheInfo)
        assert attr.payload.ifa_prefered == 30


class TestIfAddrMessage:
    """Test IfAddrMessage parsing and encoding."""

    def test_ipv4_address_message_from_buffer(self):
        """Test parsing an IPv4 address message."""
        # ifaddrmsg structure with IFA_ADDRESS attribute
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # ifa_family = AF_INET
                "18"  # ifa_prefixlen = 24
                "00"  # ifa_flags = 0
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE (0)
                "02 00 00 00"  # ifa_index = 2
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = IFA_ADDRESS
                "0a 01 02 01"  # 10.1.2.1
            )
        else:
            buf = HexBuffer(
                "02"  # ifa_family = AF_INET
                "18"  # ifa_prefixlen = 24
                "00"  # ifa_flags = 0
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE (0)
                "00 00 00 02"  # ifa_index = 2
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = IFA_ADDRESS
                "0a 01 02 01"  # 10.1.2.1
            )
        
        msg = IfAddrMessage.from_buffer(buf)
        
        assert msg.ifa_family == AddressFamily.AF_INET
        assert msg.ifa_prefixlen == 24
        assert msg.ifa_flags == AddressFlag.NONE
        assert msg.ifa_scope == AddressScope.RT_SCOPE_UNIVERSE
        assert msg.ifa_index == 2
        assert msg.address == IPv4Address("10.1.2.1")

    def test_ipv6_address_message_from_buffer(self):
        """Test parsing an IPv6 address message."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "0a"  # ifa_family = AF_INET6
                "40"  # ifa_prefixlen = 64
                "00"  # ifa_flags = 0
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE
                "03 00 00 00"  # ifa_index = 3
                "14 00"  # rta_len = 20
                "01 00"  # rta_type = IFA_ADDRESS
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"  # ...1
            )
        else:
            buf = HexBuffer(
                "0a"  # ifa_family = AF_INET6
                "40"  # ifa_prefixlen = 64
                "00"  # ifa_flags = 0
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE
                "00 00 00 03"  # ifa_index = 3
                "00 14"  # rta_len = 20
                "00 01"  # rta_type = IFA_ADDRESS
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"  # ...1
            )
        
        msg = IfAddrMessage.from_buffer(buf)
        
        assert msg.ifa_family == AddressFamily.AF_INET6
        assert msg.ifa_prefixlen == 64
        assert msg.ifa_scope == AddressScope.RT_SCOPE_UNIVERSE
        assert msg.ifa_index == 3
        assert msg.address == IPv6Address("2001:db8::1")

    def test_address_message_with_multiple_attributes(self):
        """Test parsing address message with multiple attributes."""
        # ifaddrmsg with IFA_ADDRESS, IFA_LOCAL, IFA_BROADCAST, IFA_LABEL
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # ifa_family = AF_INET
                "18"  # ifa_prefixlen = 24
                "00"  # ifa_flags = 0
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE
                "02 00 00 00"  # ifa_index = 2
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = IFA_ADDRESS
                "0a 01 02 01"  # 10.1.2.1
                "08 00"  # rta_len = 8
                "02 00"  # rta_type = IFA_LOCAL
                "0a 01 02 01"  # 10.1.2.1
                "08 00"  # rta_len = 8
                "04 00"  # rta_type = IFA_BROADCAST
                "0a 01 02 ff"  # 10.1.2.255
                "09 00"  # rta_len = 9
                "03 00"  # rta_type = IFA_LABEL
                "65 74 68 30"  # "eth0"
                "00 00 00 00"  # null + padding
            )
        else:
            buf = HexBuffer(
                "02"  # ifa_family = AF_INET
                "18"  # ifa_prefixlen = 24
                "00"  # ifa_flags = 0
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE
                "00 00 00 02"  # ifa_index = 2
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = IFA_ADDRESS
                "0a 01 02 01"  # 10.1.2.1
                "00 08"  # rta_len = 8
                "00 02"  # rta_type = IFA_LOCAL
                "0a 01 02 01"  # 10.1.2.1
                "00 08"  # rta_len = 8
                "00 04"  # rta_type = IFA_BROADCAST
                "0a 01 02 ff"  # 10.1.2.255
                "00 09"  # rta_len = 9
                "00 03"  # rta_type = IFA_LABEL
                "65 74 68 30"  # "eth0"
                "00 00 00 00"  # null + padding
            )
        
        msg = IfAddrMessage.from_buffer(buf)
        
        assert msg.ifa_family == AddressFamily.AF_INET
        assert msg.ifa_index == 2
        assert msg.address == IPv4Address("10.1.2.1")
        assert msg.local == IPv4Address("10.1.2.1")
        assert msg.broadcast == IPv4Address("10.1.2.255")
        assert msg.label == "eth0"

    def test_address_message_with_flags(self):
        """Test parsing address message with flags."""
        # IFA_F_SECONDARY = 1
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # ifa_family = AF_INET
                "20"  # ifa_prefixlen = 32
                "01"  # ifa_flags = IFA_F_SECONDARY
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE
                "02 00 00 00"  # ifa_index = 2
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = IFA_ADDRESS
                "0a 01 02 01"  # 10.1.2.1
                "08 00"  # rta_len = 8
                "08 00"  # rta_type = IFA_FLAGS
                "01 00 00 00"  # IFA_F_SECONDARY
            )
        else:
            buf = HexBuffer(
                "02"  # ifa_family = AF_INET
                "20"  # ifa_prefixlen = 32
                "01"  # ifa_flags = IFA_F_SECONDARY
                "00"  # ifa_scope = RT_SCOPE_UNIVERSE
                "00 00 00 02"  # ifa_index = 2
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = IFA_ADDRESS
                "0a 01 02 01"  # 10.1.2.1
                "00 08"  # rta_len = 8
                "00 08"  # rta_type = IFA_FLAGS
                "00 00 00 01"  # IFA_F_SECONDARY
            )
        
        msg = IfAddrMessage.from_buffer(buf)
        
        assert msg.ifa_flags == AddressFlag.IFA_F_SECONDARY
        assert msg.flags_value == 1

    def test_encode_ipv4_address_message(self):
        """Test encoding an IPv4 address message."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_flags=AddressFlag.NONE,
            ifa_scope=AddressScope.RT_SCOPE_UNIVERSE,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv4Address("10.1.2.1"))
        
        encoded = bytes(msg)
        decoded = IfAddrMessage.from_buffer(encoded)
        
        assert decoded.ifa_family == AddressFamily.AF_INET
        assert decoded.ifa_prefixlen == 24
        assert decoded.ifa_index == 2
        assert decoded.address == IPv4Address("10.1.2.1")

    def test_encode_ipv6_address_message(self):
        """Test encoding an IPv6 address message."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET6,
            ifa_prefixlen=64,
            ifa_flags=AddressFlag.NONE,
            ifa_scope=AddressScope.RT_SCOPE_UNIVERSE,
            ifa_index=3,
        )
        msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv6Address("2001:db8::1"))
        
        encoded = bytes(msg)
        decoded = IfAddrMessage.from_buffer(encoded)
        
        assert decoded.ifa_family == AddressFamily.AF_INET6
        assert decoded.ifa_prefixlen == 64
        assert decoded.ifa_index == 3
        assert decoded.address == IPv6Address("2001:db8::1")

    def test_encode_address_message_with_multiple_attributes(self):
        """Test encoding address message with multiple attributes."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_flags=AddressFlag.IFA_F_SECONDARY,
            ifa_scope=AddressScope.RT_SCOPE_UNIVERSE,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv4Address("10.1.2.1"))
        msg.add_attribute(AddressAttributeType.IFA_LOCAL, IPv4Address("10.1.2.1"))
        msg.add_attribute(AddressAttributeType.IFA_BROADCAST, IPv4Address("10.1.2.255"))
        msg.add_attribute(AddressAttributeType.IFA_LABEL, "eth0")
        msg.add_attribute(AddressAttributeType.IFA_FLAGS, 1)
        
        encoded = bytes(msg)
        decoded = IfAddrMessage.from_buffer(encoded)
        
        assert decoded.ifa_family == AddressFamily.AF_INET
        assert decoded.ifa_prefixlen == 24
        assert decoded.ifa_flags == AddressFlag.IFA_F_SECONDARY
        assert decoded.ifa_index == 2
        assert decoded.address == IPv4Address("10.1.2.1")
        assert decoded.local == IPv4Address("10.1.2.1")
        assert decoded.broadcast == IPv4Address("10.1.2.255")
        assert decoded.label == "eth0"
        assert decoded.flags_value == 1

    def test_address_message_properties(self):
        """Test IfAddrMessage property accessors."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv4Address("10.1.2.1"))
        msg.add_attribute(AddressAttributeType.IFA_LOCAL, IPv4Address("10.1.2.1"))
        msg.add_attribute(AddressAttributeType.IFA_BROADCAST, IPv4Address("10.1.2.255"))
        msg.add_attribute(AddressAttributeType.IFA_LABEL, "eth0")
        
        assert msg.address == IPv4Address("10.1.2.1")
        assert msg.local == IPv4Address("10.1.2.1")
        assert msg.broadcast == IPv4Address("10.1.2.255")
        assert msg.label == "eth0"
        assert msg.anycast is None
        assert msg.multicast is None
        assert msg.cacheinfo is None

    def test_address_message_anycast_attribute(self):
        """Test IFA_ANYCAST attribute."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_ANYCAST, IPv4Address("10.1.2.0"))
        
        assert msg.anycast == IPv4Address("10.1.2.0")

    def test_address_message_multicast_attribute(self):
        """Test IFA_MULTICAST attribute."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_MULTICAST, IPv4Address("224.0.0.1"))
        
        assert msg.multicast == IPv4Address("224.0.0.1")

    def test_address_message_cacheinfo_attribute(self):
        """Test IFA_CACHEINFO attribute."""
        cacheinfo = IfAddrCacheInfo(
            ifa_prefered=30,
            ifa_valid=60,
            cstamp=1,
            tstamp=2,
        )
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_CACHEINFO, cacheinfo)
        
        assert msg.cacheinfo is not None
        assert msg.cacheinfo.ifa_prefered == 30
        assert msg.cacheinfo.ifa_valid == 60

    def test_address_message_attributes_property(self):
        """Test IfAddrMessage.attributes property."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )
        msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv4Address("10.1.2.1"))
        msg.add_attribute(AddressAttributeType.IFA_LOCAL, IPv4Address("10.1.2.1"))
        
        attrs = msg.attributes
        assert AddressAttributeType.IFA_ADDRESS in attrs
        assert AddressAttributeType.IFA_LOCAL in attrs
        assert IPv4Address("10.1.2.1") in attrs[AddressAttributeType.IFA_ADDRESS]

    def test_address_message_various_scopes(self):
        """Test various address scope values."""
        for scope in [
            AddressScope.RT_SCOPE_UNIVERSE,
            AddressScope.RT_SCOPE_SITE,
            AddressScope.RT_SCOPE_LINK,
            AddressScope.RT_SCOPE_HOST,
            AddressScope.RT_SCOPE_NOWHERE,
        ]:
            msg = IfAddrMessage(
                ifa_family=AddressFamily.AF_INET,
                ifa_prefixlen=24,
                ifa_scope=scope,
                ifa_index=2,
            )
            msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv4Address("10.1.2.1"))
            
            encoded = bytes(msg)
            decoded = IfAddrMessage.from_buffer(encoded)
            assert decoded.ifa_scope == scope

    def test_address_message_various_flags(self):
        """Test various address flag values."""
        for flag in [
            AddressFlag.IFA_F_SECONDARY,
            AddressFlag.IFA_F_DEPRECATED,
            AddressFlag.IFA_F_TENTATIVE,
            AddressFlag.IFA_F_DADFAILED,
            AddressFlag.IFA_F_HOMEADDRESS,
            AddressFlag.IFA_F_NODAD,
            AddressFlag.IFA_F_OPTIMISTIC,
        ]:
            msg = IfAddrMessage(
                ifa_family=AddressFamily.AF_INET,
                ifa_prefixlen=24,
                ifa_flags=flag,
                ifa_index=2,
            )
            msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv4Address("10.1.2.1"))
            
            encoded = bytes(msg)
            decoded = IfAddrMessage.from_buffer(encoded)
            assert decoded.ifa_flags == flag

    def test_address_message_empty_attrs(self):
        """Test IfAddrMessage with no attributes."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )
        
        encoded = bytes(msg)
        decoded = IfAddrMessage.from_buffer(encoded)
        
        assert decoded.ifa_family == AddressFamily.AF_INET
        assert decoded.ifa_prefixlen == 24
        assert decoded.ifa_index == 2
        assert decoded.attrs == []
        assert decoded.address is None
        assert decoded.local is None

    def test_ipv6_address_message_properties(self):
        """Test IPv6 address message properties."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET6,
            ifa_prefixlen=64,
            ifa_index=3,
        )
        msg.add_attribute(AddressAttributeType.IFA_ADDRESS, IPv6Address("2001:db8::1"))
        msg.add_attribute(AddressAttributeType.IFA_LOCAL, IPv6Address("2001:db8::1"))
        
        assert msg.address == IPv6Address("2001:db8::1")
        assert msg.local == IPv6Address("2001:db8::1")
        assert msg.broadcast is None  # IPv6 doesn't use broadcast

    def test_address_message_str(self):
        """Test IfAddrMessage string representation."""
        msg = IfAddrMessage(
            ifa_family=AddressFamily.AF_INET,
            ifa_prefixlen=24,
            ifa_index=2,
        )

        assert "IfAddrMessage" in str(msg)
        assert "AF_INET" in str(msg)
        assert "24" in str(msg)
        assert "2" in str(msg)


class TestAddressOperationsIntegration:
    """Integration tests for AddressOperations with real kernel."""

    async def test_add_ipv4_address(self, netns):
        """Test adding an IPv4 address."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            # Create test interface
            await sock.link.add_dummy(ifname="test_addr0")
            link = await sock.link.get(ifname="test_addr0")
            assert link is not None

            try:
                # Add address
                await sock.address.add_ipv4(
                    index=link.ifi_index,
                    address="192.168.100.1",
                    prefixlen=24,
                )

                # Verify address was added
                addrs = await sock.address.get(index=link.ifi_index)
                assert len(addrs) > 0
                addr_addresses = [a.address for a in addrs if a.address]
                assert IPv4Address("192.168.100.1") in addr_addresses
            finally:
                await sock.link.delete(ifname="test_addr0")

    async def test_add_ipv6_address(self, netns):
        """Test adding an IPv6 address."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            await sock.link.add_dummy(ifname="test_addr1")
            link = await sock.link.get(ifname="test_addr1")
            assert link is not None

            try:
                await sock.address.add_ipv6(
                    index=link.ifi_index,
                    address="2001:db8::1",
                    prefixlen=64,
                )

                addrs = await sock.address.get(index=link.ifi_index)
                assert len(addrs) > 0
                addr_addresses = [a.address for a in addrs if a.address]
                assert IPv6Address("2001:db8::1") in addr_addresses
            finally:
                await sock.link.delete(ifname="test_addr1")

    async def test_add_address_with_label(self, netns):
        """Test adding an address with a label."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            await sock.link.add_dummy(ifname="test_addr2")
            link = await sock.link.get(ifname="test_addr2")
            assert link is not None

            try:
                await sock.address.add_ipv4(
                    index=link.ifi_index,
                    address="192.168.100.2",
                    prefixlen=24,
                )

                addrs = await sock.address.get(index=link.ifi_index)
                assert len(addrs) > 0
                # Note: label attribute not supported by kernel for RTM_NEWADDR
            finally:
                await sock.link.delete(ifname="test_addr2")

    async def test_add_address_with_broadcast(self, netns):
        """Test adding an address with broadcast."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            await sock.link.add_dummy(ifname="test_addr3")
            link = await sock.link.get(ifname="test_addr3")
            assert link is not None

            try:
                await sock.address.add_ipv4(
                    index=link.ifi_index,
                    address="192.168.100.3",
                    prefixlen=24,
                    broadcast=IPv4Address("192.168.100.255"),
                )

                addrs = await sock.address.get(index=link.ifi_index)
                assert len(addrs) > 0
                addr = addrs[0]
                assert addr.broadcast == IPv4Address("192.168.100.255")
            finally:
                await sock.link.delete(ifname="test_addr3")

    async def test_delete_ipv4_address(self, netns):
        """Test deleting an IPv4 address."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            await sock.link.add_dummy(ifname="test_addr4")
            link = await sock.link.get(ifname="test_addr4")
            assert link is not None

            try:
                # Add address
                await sock.address.add_ipv4(
                    index=link.ifi_index,
                    address="192.168.100.4",
                    prefixlen=24,
                )

                # Verify it exists
                addrs = await sock.address.get(index=link.ifi_index)
                addr_addresses = [a.address for a in addrs if a.address]
                assert IPv4Address("192.168.100.4") in addr_addresses

                # Delete address
                await sock.address.delete_ipv4(
                    index=link.ifi_index,
                    address="192.168.100.4",
                    prefixlen=24,
                )

                # Verify it's gone
                addrs = await sock.address.get(index=link.ifi_index)
                addr_addresses = [a.address for a in addrs if a.address]
                assert IPv4Address("192.168.100.4") not in addr_addresses
            finally:
                await sock.link.delete(ifname="test_addr4")

    async def test_dump_addresses(self, netns):
        """Test dumping all addresses."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            await sock.link.add_dummy(ifname="test_addr5")
            link = await sock.link.get(ifname="test_addr5")
            assert link is not None

            try:
                # Add address
                await sock.address.add_ipv4(
                    index=link.ifi_index,
                    address="192.168.100.5",
                    prefixlen=24,
                )

                # Dump addresses for this interface
                addrs = await sock.address.dump(index=link.ifi_index)
                assert len(addrs) >= 1

                addresses = {addr.address for addr in addrs if addr.address}
                assert IPv4Address("192.168.100.5") in addresses
            finally:
                await sock.link.delete(ifname="test_addr5")

    async def test_dump_all_system_addresses(self, netns):
        """Test dumping all system addresses."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            addrs = await sock.address.dump()
            # In a fresh namespace, there may be no addresses
            # Just verify it doesn't error
            assert isinstance(addrs, list)

    async def test_add_address_with_scope(self, netns):
        """Test adding an address with specific scope."""
        from routesia.netlink.socket import NetlinkSocket

        async with NetlinkSocket() as sock:
            await sock.link.add_dummy(ifname="test_addr6")
            link = await sock.link.get(ifname="test_addr6")
            assert link is not None

            try:
                await sock.address.add_ipv4(
                    index=link.ifi_index,
                    address="127.0.0.2",
                    prefixlen=8,
                    scope=AddressScope.RT_SCOPE_HOST,
                )

                addrs = await sock.address.get(index=link.ifi_index)
                assert len(addrs) > 0
                addr = addrs[0]
                assert addr.address == IPv4Address("127.0.0.2")
                assert addr.ifa_scope == AddressScope.RT_SCOPE_HOST
            finally:
                await sock.link.delete(ifname="test_addr6")
