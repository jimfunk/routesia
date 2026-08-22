"""
Tests for Netlink error messages with extended ACK support.
"""

import pytest
import struct
import sys

from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageType,
    NetlinkMessageFlags,
    NetlinkErrorMessage,
    CappedNetlinkErrorMessage,
    NetlinkMessageHeader,
    NLMSGERRAttribute,
    NLMSGERRAttrType,
)
from routesia.netlink.socket import open_netlink_connection
from routesia.netlink.rtnetlink.link.message import InterfaceInfoMessage

from tests.buffers import HexBuffer


class TestNetlinkErrorMessageParsing:
    """Test parsing of Netlink error messages."""

    def test_parse_simple_error(self):
        """Test parsing a simple error message without extended attributes."""
        # NLM_F_CAPPED set: inner msg is header only (16 bytes)
        # Total: 16 (outer hdr) + 4 (error) + 16 (inner hdr) = 36
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "24 00 00 00"  # nlmsg_len = 36
                "02 00"  # nlmsg_type = NLMSG_ERROR
                "00 02"  # nlmsg_flags (NLM_F_CAPPED)
                "01 00 00 00"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ea ff ff ff"  # error = -22
                "10 00 00 00"  # Inner msg header (16 bytes)
                "00 00"  # type
                "00 00"  # flags
                "00 00 00 00"  # seq
                "00 00 00 00"  # pid
            )
        else:
            buf = HexBuffer(
                "00 00 00 24"  # nlmsg_len = 36
                "00 02"  # nlmsg_type = NLMSG_ERROR
                "02 00"  # nlmsg_flags (NLM_F_CAPPED)
                "00 00 00 01"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ff ff ff ea"  # error = -22
                "00 00 00 10"  # Inner msg header (16 bytes)
                "00 00"  # type
                "00 00"  # flags
                "00 00 00 00"  # seq
                "00 00 00 00"  # pid
            )
        msg = NetlinkMessage.from_buffer(buf)

        assert isinstance(msg.error, NetlinkErrorMessage)
        assert msg.error.error == -22
        assert not msg.error.is_ack
        assert len(msg.error.attrs) == 0

    def test_parse_ack_message(self):
        """Test parsing a positive ACK (error == 0)."""
        # ACK has error=0, no attrs. Inner msg is 16 bytes (header only)
        # Total: 16 (outer hdr) + 4 (error) + 16 (inner hdr) = 36
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "24 00 00 00"  # nlmsg_len = 36
                "02 00"  # nlmsg_type = NLMSG_ERROR
                "00 00"  # nlmsg_flags
                "01 00 00 00"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "00 00 00 00"  # error = 0 (ACK)
                "10 00 00 00"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
            )
        else:
            buf = HexBuffer(
                "00 00 00 24"  # nlmsg_len = 36
                "00 02"  # nlmsg_type = NLMSG_ERROR
                "00 00"  # nlmsg_flags
                "00 00 00 01"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "00 00 00 00"  # error = 0 (ACK)
                "00 00 00 10"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
            )
        msg = NetlinkMessage.from_buffer(buf)

        assert isinstance(msg.error, NetlinkErrorMessage)
        assert msg.error.error == 0
        assert msg.error.is_ack
        assert str(msg.error) == "<NetlinkErrorMessage ACK>"

    def test_parse_error_with_message_attribute(self):
        """Test parsing error with NLMSGERR_ATTR_MSG."""
        # NLM_F_CAPPED set: inner msg is header only (16 bytes)
        # Total: 16 (outer hdr) + 4 (error) + 16 (inner hdr) + 20 (attrs) = 56
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "38 00 00 00"  # nlmsg_len = 56
                "02 00"  # nlmsg_type = NLMSG_ERROR
                "00 02"  # nlmsg_flags (NLM_F_CAPPED)
                "01 00 00 00"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ea ff ff ff"  # error = -22
                "10 00 00 00"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
                "14 00"  # nla_len = 20 (4 header + 16 data)
                "01 00"  # nla_type = NLMSGERR_ATTR_MSG
                "49 6e 76 61 6c 69 64 20"  # "Invalid "
                "61 72 67 75 6d 65 6e 74"  # "argument"
                "00 00 00 00"  # null + padding
            )
        else:
            buf = HexBuffer(
                "00 00 00 38"  # nlmsg_len = 56
                "00 02"  # nlmsg_type = NLMSG_ERROR
                "02 00"  # nlmsg_flags (NLM_F_CAPPED)
                "00 00 00 01"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ff ff ff ea"  # error = -22
                "00 00 00 10"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
                "00 14"  # nla_len = 20 (4 header + 16 data)
                "00 01"  # nla_type = NLMSGERR_ATTR_MSG
                "49 6e 76 61 6c 69 64 20"  # "Invalid "
                "61 72 67 75 6d 65 6e 74"  # "argument"
                "00 00 00 00"  # null + padding
            )
        msg = NetlinkMessage.from_buffer(buf)

        assert isinstance(msg.error, NetlinkErrorMessage)
        assert msg.error.error == -22
        assert len(msg.error.attrs) == 1
        assert msg.error.attrs[0].type == NLMSGERRAttrType.NLMSGERR_ATTR_MSG
        assert msg.error.error_message == "Invalid argument"

    def test_parse_error_with_offset_attribute(self):
        """Test parsing error with NLMSGERR_ATTR_OFFS."""
        # NLM_F_CAPPED set: inner msg is header only (16 bytes)
        # Total: 16 (outer hdr) + 4 (error) + 16 (inner hdr) + 8 (attrs) = 44
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "2c 00 00 00"  # nlmsg_len = 44
                "02 00"  # nlmsg_type = NLMSG_ERROR
                "00 02"  # nlmsg_flags (NLM_F_CAPPED)
                "01 00 00 00"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ea ff ff ff"  # error = -22
                "10 00 00 00"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
                "08 00"  # nla_len = 8
                "02 00"  # nla_type = NLMSGERR_ATTR_OFFS
                "20 00 00 00"  # offset = 32
            )
        else:
            buf = HexBuffer(
                "00 00 00 2c"  # nlmsg_len = 44
                "00 02"  # nlmsg_type = NLMSG_ERROR
                "02 00"  # nlmsg_flags (NLM_F_CAPPED)
                "00 00 00 01"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ff ff ff ea"  # error = -22
                "00 00 00 10"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
                "00 08"  # nla_len = 8
                "00 02"  # nla_type = NLMSGERR_ATTR_OFFS
                "00 00 00 20"  # offset = 32
            )

        msg = NetlinkMessage.from_buffer(buf)

        assert isinstance(msg.error, NetlinkErrorMessage)
        assert msg.error.error == -22
        assert len(msg.error.attrs) == 1
        assert msg.error.attrs[0].type == NLMSGERRAttrType.NLMSGERR_ATTR_OFFS
        assert msg.error.error_offset == 32

    def test_parse_error_with_cookie_attribute(self):
        """Test parsing error with NLMSGERR_ATTR_COOKIE."""
        # NLM_F_CAPPED set: inner msg is header only (16 bytes)
        # Total: 16 (outer hdr) + 4 (error) + 16 (inner hdr) + 12 (attrs) = 48
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "30 00 00 00"  # nlmsg_len = 48
                "02 00"  # nlmsg_type = NLMSG_ERROR
                "00 02"  # nlmsg_flags (NLM_F_CAPPED)
                "01 00 00 00"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ea ff ff ff"  # error = -22
                "10 00 00 00"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
                "0c 00"  # nla_len = 12
                "03 00"  # nla_type = NLMSGERR_ATTR_COOKIE
                "01 02 03 04 05 06 07 08"  # cookie value
            )
        else:
            buf = HexBuffer(
                "00 00 00 30"  # nlmsg_len = 48
                "00 02"  # nlmsg_type = NLMSG_ERROR
                "02 00"  # nlmsg_flags (NLM_F_CAPPED)
                "00 00 00 01"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ff ff ff ea"  # error = -22
                "00 00 00 10"  # Inner msg header (16 bytes)
                "00 00"
                "00 00"
                "00 00 00 00"
                "00 00 00 00"
                "00 0c"  # nla_len = 12
                "00 03"  # nla_type = NLMSGERR_ATTR_COOKIE
                "01 02 03 04 05 06 07 08"  # cookie value
            )

        msg = NetlinkMessage.from_buffer(buf)

        assert isinstance(msg.error, NetlinkErrorMessage)
        assert msg.error.error == -22
        assert len(msg.error.attrs) == 1
        assert msg.error.attrs[0].type == NLMSGERRAttrType.NLMSGERR_ATTR_COOKIE

    def test_parse_error_with_multiple_attributes(self):
        """Test parsing error with multiple extended attributes."""
        # NLM_F_CAPPED NOT set: inner msg includes full payload
        # For this test, the inner message is just a header (16 bytes)
        # Error payload: 4 (error) + 16 (msg) + 24 (msg attr) + 8 (offs attr) = 52
        # Outer nlmsg_len: 16 (outer hdr) + 52 (error payload) = 68
        if sys.byteorder == 'little':
            buf = HexBuffer(
                "44 00 00 00"  # nlmsg_len = 68
                "02 00"  # nlmsg_type = NLMSG_ERROR
                "00 00"  # nlmsg_flags (NOT capped)
                "01 00 00 00"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ea ff ff ff"  # error = -22
                "10 00 00 00"  # Inner msg header (16 bytes, nlmsg_len=16)
                "00 00"  # type
                "00 00"  # flags
                "00 00 00 00"  # seq
                "00 00 00 00"  # pid
                "18 00"  # nla_len = 24 (MSG attr: 4 header + 16 payload + 4 padding)
                "01 00"  # nla_type = NLMSGERR_ATTR_MSG
                "4f 70 65 72 61 74 69 6f"  # "Operatio"
                "6e 20 66 61 69 6c 65 64"  # "n failed"
                "00 00 00 00"  # null + padding
                "08 00"  # nla_len = 8 (OFFS attr)
                "02 00"  # nla_type = NLMSGERR_ATTR_OFFS
                "10 00 00 00"  # offset = 16
            )
        else:
            buf = HexBuffer(
                "00 00 00 44"  # nlmsg_len = 68
                "00 02"  # nlmsg_type = NLMSG_ERROR
                "00 00"  # nlmsg_flags (NOT capped)
                "00 00 00 01"  # nlmsg_seq
                "00 00 00 00"  # nlmsg_pid
                "ff ff ff ea"  # error = -22
                "00 00 00 10"  # Inner msg header (16 bytes, nlmsg_len=16)
                "00 00"  # type
                "00 00"  # flags
                "00 00 00 00"  # seq
                "00 00 00 00"  # pid
                "00 18"  # nla_len = 24 (MSG attr: 4 header + 16 payload + 4 padding)
                "00 01"  # nla_type = NLMSGERR_ATTR_MSG
                "4f 70 65 72 61 74 69 6f"  # "Operatio"
                "6e 20 66 61 69 6c 65 64"  # "n failed"
                "00 00 00 00"  # null + padding
                "00 08"  # nla_len = 8 (OFFS attr)
                "00 02"  # nla_type = NLMSGERR_ATTR_OFFS
                "00 00 00 10"  # offset = 16
            )

        msg = NetlinkMessage.from_buffer(buf)

        assert isinstance(msg.error, NetlinkErrorMessage)
        assert msg.error.error == -22
        assert len(msg.error.attrs) == 2
        assert msg.error.error_message == "Operation failed"
        assert msg.error.error_offset == 16


class TestNetlinkErrorMessageEncoding:
    """Test encoding of Netlink error messages."""

    def test_encode_simple_error(self):
        """Test encoding a simple error message."""
        error_msg = NetlinkErrorMessage(error=-22, msg=b"\x00" * 16, attrs=[])

        encoded = bytes(error_msg)
        assert len(encoded) == 20  # 4 (error) + 16 (msg)
        assert encoded[:4] == struct.pack('<i', -22)

    def test_encode_ack(self):
        """Test encoding a positive ACK."""
        error_msg = NetlinkErrorMessage(error=0, msg=b"\x00" * 16, attrs=[])

        encoded = bytes(error_msg)
        assert encoded[:4] == struct.pack('<i', 0)


class TestNetlinkErrorExtendedACK:
    """Integration tests for extended ACK with real kernel."""

    async def test_receive_ack_is_capped(self, netns):
        """Test that successful ACKs have NLM_F_CAPPED set (kernel trims payload)."""
        reader, writer = await open_netlink_connection()

        # Send a valid request that should succeed
        # RTM_GETLINK for interface index 1 (lo) should succeed
        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=InterfaceInfoMessage(ifi_index=1),
        )
        writer.write(msg)

        # Should receive response (RTM_NEWLINK) followed by ACK (NLMSG_ERROR with error=0)
        response = await reader.read()
        assert response.nlmsg_type == NetlinkMessageType.RTM_NEWLINK

        # ACK has NLM_F_CAPPED set - kernel trims original payload for success
        ack = await reader.read()
        assert ack.nlmsg_type == NetlinkMessageType.NLMSG_ERROR
        assert ack.nlmsg_flags & NetlinkMessageFlags.NLM_F_CAPPED
        assert isinstance(ack.error, CappedNetlinkErrorMessage)
        assert ack.error.is_ack
        assert ack.error.error == 0

        writer.close()

    async def test_receive_error_is_not_capped(self, netns):
        """Test that errors without NETLINK_CAP_ACK include full original payload."""
        reader, writer = await open_netlink_connection()

        # Send an invalid request to trigger an error
        # RTM_DELLINK with invalid index should fail
        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_DELLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=InterfaceInfoMessage(ifi_index=99999),
        )
        writer.write(msg)

        # Should receive error
        # With NETLINK_EXT_ACK (not NETLINK_CAP_ACK), errors have NLM_F_CAPPED cleared
        # and include the full original message payload
        response = await reader.read()
        assert response.nlmsg_type == NetlinkMessageType.NLMSG_ERROR
        assert not (response.nlmsg_flags & NetlinkMessageFlags.NLM_F_CAPPED)
        assert isinstance(response.error, NetlinkErrorMessage)
        assert not response.error.is_ack
        assert response.error.error < 0
        # Original message header should be included
        assert isinstance(response.error.msg, NetlinkMessage)
        assert response.error.msg.nlmsg_type == NetlinkMessageType.RTM_DELLINK

        writer.close()
