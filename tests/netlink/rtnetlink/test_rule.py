"""
Tests for rtnetlink routing rule messages (rtfibmsg).
"""

import pytest
from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily
import sys

from routesia.netlink import constants
from routesia.netlink.rtnetlink.rule.message import (
    RuleMessage,
    RuleAttribute,
    RuleUidRange,
    RulePortRange,
    RuleAttributeType,
    RuleAction,
    RuleFlag,
)
from routesia.protoclass.types import UInt32

from tests.buffers import HexBuffer


class TestRuleUidRange:
    """Test RuleUidRange structure."""

    def test_uid_range_from_buffer(self):
        """Test parsing RuleUidRange."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "e8 03 00 00"  # start = 1000 (little endian)
                "d0 07 00 00"  # end = 2000 (little endian)
            )
        else:
            buf = HexBuffer(
                "00 00 03 e8"  # start = 1000 (big endian)
                "00 00 07 d0"  # end = 2000 (big endian)
            )
        
        uid_range = RuleUidRange.from_buffer(buf)
        
        assert uid_range.start == 1000
        assert uid_range.end == 2000

    def test_uid_range_to_bytes(self):
        """Test encoding RuleUidRange."""
        uid_range = RuleUidRange(start=1000, end=2000)
        
        encoded = bytes(uid_range)
        decoded = RuleUidRange.from_buffer(encoded)
        
        assert decoded.start == 1000
        assert decoded.end == 2000


class TestRulePortRange:
    """Test RulePortRange structure."""

    def test_port_range_from_buffer(self):
        """Test parsing RulePortRange."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "50 00"  # start = 80
                "c0 00"  # end = 192
            )
        else:
            buf = HexBuffer(
                "00 50"  # start = 80
                "00 c0"  # end = 192
            )
        
        port_range = RulePortRange.from_buffer(buf)
        
        assert port_range.start == 80
        assert port_range.end == 192

    def test_port_range_to_bytes(self):
        """Test encoding RulePortRange."""
        port_range = RulePortRange(start=80, end=443)
        
        encoded = bytes(port_range)
        decoded = RulePortRange.from_buffer(encoded)
        
        assert decoded.start == 80
        assert decoded.end == 443


class TestRuleAttribute:
    """Test RuleAttribute parsing and encoding."""

    def test_attribute_ipv4_dst(self):
        """Test FRA_DST attribute with IPv4."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = FRA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = FRA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        
        attr = RuleAttribute.from_buffer(buf)
        
        assert attr.rta_len == 8
        assert attr.type == RuleAttributeType.FRA_DST
        assert attr.payload == IPv4Address("10.1.1.1")

    def test_attribute_ipv6_dst(self):
        """Test FRA_DST attribute with IPv6."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "14 00"  # rta_len = 20
                "01 00"  # rta_type = FRA_DST
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        else:
            buf = HexBuffer(
                "00 14"  # rta_len = 20
                "00 01"  # rta_type = FRA_DST
                "20 01 0d b8 00 00 00 00"  # 2001:db8::
                "00 00 00 00 00 00 00 01"
            )
        
        attr = RuleAttribute.from_buffer(buf)
        
        assert attr.rta_len == 20
        assert attr.type == RuleAttributeType.FRA_DST
        assert attr.payload == IPv6Address("2001:db8::1")

    def test_attribute_iifname(self):
        """Test FRA_IIFNAME attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "09 00"  # rta_len = 9
                "03 00"  # rta_type = FRA_IIFNAME
                "65 74 68 30"  # "eth0"
                "00 00 00 00"  # null + padding
            )
        else:
            buf = HexBuffer(
                "00 09"  # rta_len = 9
                "00 03"  # rta_type = FRA_IIFNAME
                "65 74 68 30"  # "eth0"
                "00 00 00 00"  # null + padding
            )
        
        attr = RuleAttribute.from_buffer(buf)
        
        assert attr.type == RuleAttributeType.FRA_IIFNAME
        assert attr.payload == "eth0"

    def test_attribute_priority(self):
        """Test FRA_PRIORITY attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "06 00"  # rta_type = FRA_PRIORITY
                "05 00 00 00"  # priority 5
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 06"  # rta_type = FRA_PRIORITY
                "00 00 00 05"  # priority 5
            )
        
        attr = RuleAttribute.from_buffer(buf)
        
        assert attr.type == RuleAttributeType.FRA_PRIORITY
        assert attr.payload == 5

    def test_attribute_fwmark(self):
        """Test FRA_FWMARK attribute."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "08 00"  # rta_len = 8
                "0a 00"  # rta_type = FRA_FWMARK (10)
                "0a 00 00 00"  # fwmark 10 (little endian)
            )
        else:
            buf = HexBuffer(
                "00 08"  # rta_len = 8
                "00 0a"  # rta_type = FRA_FWMARK (10)
                "00 00 00 0a"  # fwmark 10 (big endian)
            )
        
        attr = RuleAttribute.from_buffer(buf)
        
        assert attr.type == RuleAttributeType.FRA_FWMARK
        assert attr.payload == 10


class TestRuleMessage:
    """Test RuleMessage parsing and encoding."""

    def test_rule_from_buffer(self):
        """Test parsing a routing rule."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # rtm_family = AF_INET
                "20"  # rtm_dst_len = 32
                "00"  # rtm_src_len = 0
                "00"  # rtm_tos = 0
                "fe"  # rtm_table = 254 (main)
                "00"  # rtm_action = FR_ACT_UNSPEC
                "00 00 00 00"  # rtm_flags = 0
                "08 00"  # rta_len = 8
                "01 00"  # rta_type = FRA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        else:
            buf = HexBuffer(
                "02"  # rtm_family = AF_INET
                "20"  # rtm_dst_len = 32
                "00"  # rtm_src_len = 0
                "00"  # rtm_tos = 0
                "fe"  # rtm_table = 254 (main)
                "00"  # rtm_action = FR_ACT_UNSPEC
                "00 00 00 00"  # rtm_flags = 0
                "00 08"  # rta_len = 8
                "00 01"  # rta_type = FRA_DST
                "0a 01 01 01"  # 10.1.1.1
            )
        
        msg = RuleMessage.from_buffer(buf)
        
        assert msg.rtm_family == AddressFamily.AF_INET
        assert msg.rtm_dst_len == 32
        assert msg.rtm_table == 254
        assert msg.dst == IPv4Address("10.1.1.1")

    def test_rule_with_priority(self):
        """Test parsing rule with priority."""
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "02"  # rtm_family = AF_INET
                "00"  # rtm_dst_len = 0
                "00"  # rtm_src_len = 0
                "00"  # rtm_tos = 0
                "05"  # rtm_table = 5
                "00"  # rtm_action = FR_ACT_UNSPEC
                "00 00 00 00"  # rtm_flags = 0
                "08 00"  # rta_len = 8
                "06 00"  # rta_type = FRA_PRIORITY
                "0a 00 00 00"  # priority 10
            )
        else:
            buf = HexBuffer(
                "02"  # rtm_family = AF_INET
                "00"  # rtm_dst_len = 0
                "00"  # rtm_src_len = 0
                "00"  # rtm_tos = 0
                "05"  # rtm_table = 5
                "00"  # rtm_action = FR_ACT_UNSPEC
                "00 00 00 00"  # rtm_flags = 0
                "00 08"  # rta_len = 8
                "00 06"  # rta_type = FRA_PRIORITY
                "00 00 00 0a"  # priority 10
            )
        
        msg = RuleMessage.from_buffer(buf)
        
        assert msg.rtm_table == 5
        assert msg.priority == 10

    def test_encode_rule(self):
        """Test encoding a routing rule."""
        msg = RuleMessage(
            rtm_family=AddressFamily.AF_INET,
            rtm_dst_len=32,
            rtm_src_len=0,
            rtm_tos=0,
            rtm_table=254,
            rtm_action=RuleAction.FR_ACT_UNSPEC,
            rtm_flags=RuleFlag.NONE,
        )
        msg.add_attribute(RuleAttributeType.FRA_DST, IPv4Address("10.1.1.1"))
        msg.add_attribute(RuleAttributeType.FRA_PRIORITY, 100)
        
        encoded = bytes(msg)
        decoded = RuleMessage.from_buffer(encoded)
        
        assert decoded.rtm_family == AddressFamily.AF_INET
        assert decoded.rtm_table == 254
        assert decoded.dst == IPv4Address("10.1.1.1")
        assert decoded.priority == 100

    def test_rule_properties(self):
        """Test RuleMessage property accessors."""
        msg = RuleMessage(
            rtm_family=AddressFamily.AF_INET,
            rtm_table=10,
        )
        msg.add_attribute(RuleAttributeType.FRA_DST, IPv4Address("192.168.1.0"))
        msg.add_attribute(RuleAttributeType.FRA_SRC, IPv4Address("10.0.0.0"))
        msg.add_attribute(RuleAttributeType.FRA_IIFNAME, "eth0")
        msg.add_attribute(RuleAttributeType.FRA_PRIORITY, 50)
        msg.add_attribute(RuleAttributeType.FRA_FWMARK, 100)
        
        assert msg.dst == IPv4Address("192.168.1.0")
        assert msg.src == IPv4Address("10.0.0.0")
        assert msg.iifname == "eth0"
        assert msg.priority == 50
        assert msg.fwmark == 100
        assert msg.flow is None
        assert msg.table_id is None

    def test_rule_str(self):
        """Test RuleMessage string representation."""
        msg = RuleMessage(
            rtm_family=AddressFamily.AF_INET,
            rtm_table=10,
            rtm_action=RuleAction.FR_ACT_TO_TBL,
        )
        
        assert "RuleMessage" in str(msg)
        assert "AF_INET" in str(msg)
        assert "10" in str(msg)
        assert "TO_TBL" in str(msg)

    def test_rule_various_actions(self):
        """Test various rule action values."""
        for action in [
            RuleAction.FR_ACT_UNSPEC,
            RuleAction.FR_ACT_TO_TBL,
            RuleAction.FR_ACT_GOTO,
            RuleAction.FR_ACT_NOP,
            RuleAction.FR_ACT_BLACKHOLE,
            RuleAction.FR_ACT_UNREACHABLE,
            RuleAction.FR_ACT_PROHIBIT,
        ]:
            msg = RuleMessage(
                rtm_family=AddressFamily.AF_INET,
                rtm_table=0,
                rtm_action=action,
            )
            
            encoded = bytes(msg)
            decoded = RuleMessage.from_buffer(encoded)
            assert decoded.rtm_action == action
