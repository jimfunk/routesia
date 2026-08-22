from typing import Annotated, Union
from enum import IntEnum, IntFlag

from routesia.netlink import constants
from routesia.netlink.exceptions import NetlinkMessageException
from routesia.netlink.rtnetlink.link.message import InterfaceInfoMessage
from routesia.netlink.rtnetlink.route.message import RouteMessage
from routesia.netlink.rtnetlink.address.message import IfAddrMessage
from routesia.netlink.rtnetlink.neighbor.message import NeighbourMessage
from routesia.netlink.rtnetlink.rule.message import RuleMessage
from routesia.protoclass import (
    Bytes,
    protoclass,
    TypeMap,
    VariableLengthData,
    UInt16,
    UInt16Base,
    UInt32,
    UInt32Base,
    UInt64,
    Int32,
)
from routesia.protoclass.types import NullTerminatedString


class NetlinkMessageType(UInt16Base, IntEnum):
    """
    Netlink message type
    """

    NLMSG_NOOP = constants.NLMSG_NOOP
    NLMSG_ERROR = constants.NLMSG_ERROR
    NLMSG_DONE = constants.NLMSG_DONE
    NLMSG_OVERRUN = constants.NLMSG_OVERRUN
    RTM_NEWLINK = constants.RTM_NEWLINK
    RTM_DELLINK = constants.RTM_DELLINK
    RTM_GETLINK = constants.RTM_GETLINK
    RTM_SETLINK = constants.RTM_SETLINK
    RTM_NEWADDR = constants.RTM_NEWADDR
    RTM_DELADDR = constants.RTM_DELADDR
    RTM_GETADDR = constants.RTM_GETADDR
    RTM_NEWROUTE = constants.RTM_NEWROUTE
    RTM_DELROUTE = constants.RTM_DELROUTE
    RTM_GETROUTE = constants.RTM_GETROUTE
    RTM_NEWNEIGH = constants.RTM_NEWNEIGH
    RTM_DELNEIGH = constants.RTM_DELNEIGH
    RTM_GETNEIGH = constants.RTM_GETNEIGH
    RTM_NEWRULE = constants.RTM_NEWRULE
    RTM_DELRULE = constants.RTM_DELRULE
    RTM_GETRULE = constants.RTM_GETRULE
    RTM_NEWQDISC = constants.RTM_NEWQDISC
    RTM_DELQDISC = constants.RTM_DELQDISC
    RTM_GETQDISC = constants.RTM_GETQDISC
    RTM_NEWTCLASS = constants.RTM_NEWTCLASS
    RTM_DELTCLASS = constants.RTM_DELTCLASS
    RTM_GETTCLASS = constants.RTM_GETTCLASS
    RTM_NEWTFILTER = constants.RTM_NEWTFILTER
    RTM_DELTFILTER = constants.RTM_DELTFILTER
    RTM_GETTFILTER = constants.RTM_GETTFILTER
    RTM_NEWACTION = constants.RTM_NEWACTION
    RTM_DELACTION = constants.RTM_DELACTION
    RTM_GETACTION = constants.RTM_GETACTION
    RTM_NEWPREFIX = constants.RTM_NEWPREFIX
    RTM_GETMULTICAST = constants.RTM_GETMULTICAST
    RTM_GETANYCAST = constants.RTM_GETANYCAST
    RTM_NEWNEIGHTBL = constants.RTM_NEWNEIGHTBL
    RTM_GETNEIGHTBL = constants.RTM_GETNEIGHTBL
    RTM_SETNEIGHTBL = constants.RTM_SETNEIGHTBL
    RTM_NEWNDUSEROPT = constants.RTM_NEWNDUSEROPT
    RTM_NEWADDRLABEL = constants.RTM_NEWADDRLABEL
    RTM_DELADDRLABEL = constants.RTM_DELADDRLABEL
    RTM_GETADDRLABEL = constants.RTM_GETADDRLABEL
    RTM_GETDCB = constants.RTM_GETDCB
    RTM_SETDCB = constants.RTM_SETDCB
    RTM_NEWNETCONF = constants.RTM_NEWNETCONF
    RTM_DELNETCONF = constants.RTM_DELNETCONF
    RTM_GETNETCONF = constants.RTM_GETNETCONF
    RTM_NEWMDB = constants.RTM_NEWMDB
    RTM_DELMDB = constants.RTM_DELMDB
    RTM_GETMDB = constants.RTM_GETMDB
    RTM_NEWNSID = constants.RTM_NEWNSID
    RTM_DELNSID = constants.RTM_DELNSID
    RTM_GETNSID = constants.RTM_GETNSID
    RTM_NEWSTATS = constants.RTM_NEWSTATS
    RTM_GETSTATS = constants.RTM_GETSTATS
    RTM_NEWCACHEREPORT = constants.RTM_NEWCACHEREPORT
    RTM_NEWCHAIN = constants.RTM_NEWCHAIN
    RTM_DELCHAIN = constants.RTM_DELCHAIN
    RTM_GETCHAIN = constants.RTM_GETCHAIN
    RTM_NEWNEXTHOP = constants.RTM_NEWNEXTHOP
    RTM_DELNEXTHOP = constants.RTM_DELNEXTHOP
    RTM_GETNEXTHOP = constants.RTM_GETNEXTHOP
    RTM_NEWLINKPROP = constants.RTM_NEWLINKPROP
    RTM_DELLINKPROP = constants.RTM_DELLINKPROP
    RTM_GETLINKPROP = constants.RTM_GETLINKPROP
    RTM_NEWNVLAN = constants.RTM_NEWNVLAN
    RTM_DELVLAN = constants.RTM_DELVLAN
    RTM_GETVLAN = constants.RTM_GETVLAN
    RTM_NEWNEXTHOPBUCKET = constants.RTM_NEWNEXTHOPBUCKET
    RTM_DELNEXTHOPBUCKET = constants.RTM_DELNEXTHOPBUCKET
    RTM_GETNEXTHOPBUCKET = constants.RTM_GETNEXTHOPBUCKET


class NLMSGERRAttrType(UInt16Base, IntEnum):
    """
    NLMSGERR attribute types for extended ACK
    """

    NLMSGERR_ATTR_UNUSED = constants.NLMSGERR_ATTR_UNUSED
    NLMSGERR_ATTR_MSG = constants.NLMSGERR_ATTR_MSG
    NLMSGERR_ATTR_OFFS = constants.NLMSGERR_ATTR_OFFS
    NLMSGERR_ATTR_COOKIE = constants.NLMSGERR_ATTR_COOKIE
    NLMSGERR_ATTR_POLICY = constants.NLMSGERR_ATTR_POLICY
    NLMSGERR_ATTR_MISS_TYPE = getattr(constants, "NLMSGERR_ATTR_MISS_TYPE", 6)
    NLMSGERR_ATTR_MISS_NEST = getattr(constants, "NLMSGERR_ATTR_MISS_NEST", 7)


@protoclass()
class NLMSGERRAttribute:
    """
    NLMSGERR extended ACK attribute using standard nlattr format
    """

    nla_len: UInt16
    nla_type: UInt16
    payload: TypeMap(
        length_field="nla_len",
        length_offset=-4,
        type_field="nla_type",
        type_map={
            NLMSGERRAttrType.NLMSGERR_ATTR_MSG: NullTerminatedString,
            NLMSGERRAttrType.NLMSGERR_ATTR_OFFS: UInt32,
            NLMSGERRAttrType.NLMSGERR_ATTR_COOKIE: UInt64,
        },
        align=4,
    )

    @property
    def type(self) -> int:
        return self.nla_type & constants.NLA_TYPE_MASK


class NetlinkMessageFlags(UInt16Base, IntFlag):
    """
    Netlink message flags
    """

    NONE = 0
    NLM_F_REQUEST = constants.NLM_F_REQUEST
    NLM_F_MULTI = constants.NLM_F_MULTI
    NLM_F_ACK = constants.NLM_F_ACK
    NLM_F_ECHO = constants.NLM_F_ECHO
    NLM_F_DUMP_INTR = constants.NLM_F_DUMP_INTR
    NLM_F_DUMP_FILTERED = constants.NLM_F_DUMP_FILTERED
    NLM_F_ROOT = constants.NLM_F_ROOT
    NLM_F_MATCH = constants.NLM_F_MATCH
    NLM_F_ATOMIC = constants.NLM_F_ATOMIC
    NLM_F_DUMP = constants.NLM_F_DUMP
    NLM_F_REPLACE = constants.NLM_F_REPLACE
    NLM_F_EXCL = constants.NLM_F_EXCL
    NLM_F_CREATE = constants.NLM_F_CREATE
    NLM_F_APPEND = constants.NLM_F_APPEND
    NLM_F_NONREC = constants.NLM_F_NONREC
    NLM_F_CAPPED = constants.NLM_F_CAPPED
    NLM_F_ACK_TLVS = constants.NLM_F_ACK_TLVS


class NetlinkGroup(UInt32Base, IntFlag):
    """
    Netlink multicast groups
    """

    NONE = 0
    RTMGRP_LINK = 1
    RTMGRP_NOTIFY = 2
    RTMGRP_NEIGH = 4
    RTMGRP_TC = 8
    RTMGRP_IPV4_IFADDR = 0x10
    RTMGRP_IPV4_MROUTE = 0x20
    RTMGRP_IPV4_ROUTE = 0x40
    RTMGRP_IPV4_RULE = 0x80
    RTMGRP_IPV6_IFADDR = 0x100
    RTMGRP_IPV6_MROUTE = 0x200
    RTMGRP_IPV6_ROUTE = 0x400
    RTMGRP_IPV6_IFINFO = 0x800
    RTMGRP_DECnet_IFADDR = 0x1000
    RTMGRP_DECnet_ROUTE = 0x4000
    RTMGRP_IPV6_PREFIX = 0x20000


def nlmsg_align(length: int) -> int:
    """
    Get the space required for nlmsg length after alignment
    """
    return (length + 3) & ~3


@protoclass()
class NetlinkMessage:
    """
    Netlink message header with variable payload
    """

    nlmsg_len: UInt32
    nlmsg_type: Annotated[NetlinkMessageType, UInt16]
    nlmsg_flags: Annotated[NetlinkMessageFlags, UInt16]
    nlmsg_seq: UInt32
    nlmsg_pid: UInt32
    payload: Annotated[
        Union[Bytes, InterfaceInfoMessage, RouteMessage],
        VariableLengthData(
            length_field="nlmsg_len",
            length_offset=-16,  # subtract header size
            type_field="nlmsg_type",
            type_map={
                # Base netlink message types
                NetlinkMessageType.NLMSG_NOOP: Bytes,
                NetlinkMessageType.NLMSG_ERROR: Bytes,
                NetlinkMessageType.NLMSG_DONE: Bytes,
                NetlinkMessageType.NLMSG_OVERRUN: Bytes,
                # rtnetlink message types
                NetlinkMessageType.RTM_NEWLINK: InterfaceInfoMessage,
                NetlinkMessageType.RTM_DELLINK: InterfaceInfoMessage,
                NetlinkMessageType.RTM_GETLINK: InterfaceInfoMessage,
                NetlinkMessageType.RTM_SETLINK: InterfaceInfoMessage,
                NetlinkMessageType.RTM_NEWADDR: IfAddrMessage,
                NetlinkMessageType.RTM_DELADDR: IfAddrMessage,
                NetlinkMessageType.RTM_GETADDR: IfAddrMessage,
                NetlinkMessageType.RTM_NEWNEIGH: NeighbourMessage,
                NetlinkMessageType.RTM_DELNEIGH: NeighbourMessage,
                NetlinkMessageType.RTM_GETNEIGH: NeighbourMessage,
                NetlinkMessageType.RTM_NEWRULE: RuleMessage,
                NetlinkMessageType.RTM_DELRULE: RuleMessage,
                NetlinkMessageType.RTM_GETRULE: RuleMessage,
                NetlinkMessageType.RTM_NEWROUTE: RouteMessage,
                NetlinkMessageType.RTM_DELROUTE: RouteMessage,
                NetlinkMessageType.RTM_GETROUTE: RouteMessage,
            },
            align=4,
        ),
    ]

    def __str__(self) -> str:
        return f"<NetlinkMessage type={self.nlmsg_type.name} flags={self.nlmsg_flags.name} payload={self.payload}>"

    @property
    def attributes(self):
        if hasattr(self.payload, "attributes"):
            return self.payload.attributes
        return {}

    @property
    def aligned_nlmsg_len(self) -> int:
        return nlmsg_align(self.nlmsg_len)

    @property
    def error(self) -> "NetlinkErrorMessage | CappedNetlinkErrorMessage":
        """
        Parse and return appropriate error message type.

        Uses outer NLM_F_CAPPED flag to determine which type to parse.
        """
        if self.nlmsg_type != NetlinkMessageType.NLMSG_ERROR:
            raise NetlinkMessageException(f"Not an error message: {self.nlmsg_type}")

        # Check outer NLM_F_CAPPED flag
        if self.nlmsg_flags & NetlinkMessageFlags.NLM_F_CAPPED:
            return CappedNetlinkErrorMessage.from_buffer(self.payload)

        # Not capped - parse with full message
        return NetlinkErrorMessage.from_buffer(self.payload)


@protoclass()
class NetlinkMessageHeader:
    """
    Netlink message header only (16 bytes).

    Used for embedded message headers in error messages where the payload
    is not needed or already parsed separately.
    """
    nlmsg_len: UInt32
    nlmsg_type: Annotated[NetlinkMessageType, UInt16]
    nlmsg_flags: Annotated[NetlinkMessageFlags, UInt16]
    nlmsg_seq: UInt32
    nlmsg_pid: UInt32
    # No payload field - header only


@protoclass()
class NetlinkErrorMessage:
    """
    Netlink error message when NLM_F_CAPPED is NOT set.

    The original message payload IS included after the header.

    Structure:
    - error: Int32 (4 bytes)
    - msg: Full original message (nlmsghdr + payload)
    - attrs: NLMSGERR attributes (remaining bytes)

    Note: msg.payload is Bytes to avoid circular dependency.
    """
    error: Int32
    msg: NetlinkMessage
    attrs: Annotated[
        list[NLMSGERRAttribute],
        VariableLengthData(item_type=NLMSGERRAttribute, align=4),
    ]

    @property
    def is_ack(self) -> bool:
        return self.error == 0

    @property
    def error_message(self) -> str | None:
        for attr in self.attrs:
            if attr.type == NLMSGERRAttrType.NLMSGERR_ATTR_MSG:
                return str(attr.payload)
        return None

    @property
    def error_offset(self) -> int | None:
        for attr in self.attrs:
            if attr.type == NLMSGERRAttrType.NLMSGERR_ATTR_OFFS:
                return int(attr.payload)
        return None

    def __str__(self) -> str:
        if self.is_ack:
            return "<NetlinkErrorMessage ACK>"
        error_str = f"error={self.error}"
        if self.error_message:
            error_str += f" message={self.error_message!r}"
        if self.error_offset is not None:
            error_str += f" offset={self.error_offset}"
        return f"<NetlinkErrorMessage {error_str}>"


@protoclass()
class CappedNetlinkErrorMessage:
    """
    Netlink error message when NLM_F_CAPPED is set.

    The original message payload is omitted - only the 16-byte header is included.

    Structure:
    - error: Int32 (4 bytes)
    - msg: nlmsghdr only (16 bytes, no payload)
    - attrs: NLMSGERR attributes (if NETLINK_EXT_ACK set)
    """
    error: Int32
    msg: NetlinkMessageHeader
    attrs: Annotated[
        list[NLMSGERRAttribute],
        VariableLengthData(item_type=NLMSGERRAttribute, align=4),
    ]

    @property
    def is_ack(self) -> bool:
        return self.error == 0

    @property
    def error_message(self) -> str | None:
        for attr in self.attrs:
            if attr.type == NLMSGERRAttrType.NLMSGERR_ATTR_MSG:
                return str(attr.payload)
        return None

    @property
    def error_offset(self) -> int | None:
        for attr in self.attrs:
            if attr.type == NLMSGERRAttrType.NLMSGERR_ATTR_OFFS:
                return int(attr.payload)
        return None

    def __str__(self) -> str:
        if self.is_ack:
            return "<CappedNetlinkErrorMessage ACK>"
        error_str = f"error={self.error}"
        if self.error_message:
            error_str += f" message={self.error_message!r}"
        if self.error_offset is not None:
            error_str += f" offset={self.error_offset}"
        return f"<CappedNetlinkErrorMessage {error_str}>"


def nlmsg_length(payload_len: int) -> int:
    """
    Get the length of nlmsg payload plus header
    """
    return payload_len + 16  # Fixed header size


def nlmsg_space(payload_len: int) -> int:
    """
    Get the full space required for nlmsg payload plus header after alignment
    """
    return nlmsg_align(nlmsg_length(payload_len))
