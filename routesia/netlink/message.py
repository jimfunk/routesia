from ctypes import (
    Structure,
    c_uint16,
    c_uint32,
    sizeof,
)
from enum import IntEnum, IntFlag

from routesia.netlink import constants
from routesia.netlink.rtnetlink.message import RTNetlinkMessage
from routesia.netlink.rtnetlink.interface import InterfaceInfoMessage
from routesia.netlink.rtnetlink.route import RouteMessage


class NetlinkMessageType(IntEnum):
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


class NetlinkMessageFlags(IntFlag):
    """
    Netlink message flags
    """

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


def nlmsg_align(length: int) -> int:
    """
    Get the space required for nlmsg length after alignment
    """
    return (length + 3) & ~3


def nlmsg_length(payload_len: int) -> int:
    """
    Get the length of nlmsg payload plus header
    """
    return payload_len + sizeof(NetlinkMessage)


def nlmsg_space(payload_len: int) -> int:
    """
    Get the full space required for nlmsg payload plus header after alignment
    """
    return nlmsg_align(nlmsg_length(payload_len))


class NetlinkMessage(Structure):
    _fields_ = [
        ("nlmsg_len", c_uint32),
        ("_nlmsg_type", c_uint16),
        ("_nlmsg_flags", c_uint16),
        ("nlmsg_seq", c_uint32),
        ("nlmsg_pid", c_uint32),
    ]
    nlmsg_len: int
    nlmsg_seq: int
    nlmsg_pid: int

    _nlmsg_type_map = {
        NetlinkMessageType.RTM_NEWLINK: InterfaceInfoMessage,
        NetlinkMessageType.RTM_DELLINK: InterfaceInfoMessage,
        NetlinkMessageType.RTM_GETLINK: InterfaceInfoMessage,
        NetlinkMessageType.RTM_SETLINK: InterfaceInfoMessage,
        NetlinkMessageType.RTM_NEWROUTE: RouteMessage,
        NetlinkMessageType.RTM_DELROUTE: RouteMessage,
        NetlinkMessageType.RTM_GETROUTE: RouteMessage,
    }

    def __init__(
        self,
        nlmsg_type: NetlinkMessageType | None = None,
        nlmsg_flags: NetlinkMessageFlags | None = None,
        nlmsg_seq: int = 0,
        nlmsg_pid: int = 0,
        payload: RTNetlinkMessage | bytes = b"",
    ):
        super().__init__(

        )
        self.payload = payload
        if nlmsg_type is not None:
            self.nlmsg_type = nlmsg_type
        if nlmsg_flags is not None:
            self.nlmsg_flags = nlmsg_flags
        self.nlmsg_seq = nlmsg_seq
        self.nlmsg_pid = nlmsg_pid

    def __len__(self):
        return nlmsg_align(self.nlmsg_len)

    def __bytes__(self) -> bytes:
        padding = nlmsg_align(self.nlmsg_len) - self.nlmsg_len
        return bytes(memoryview(self)) + bytes(self._payload) + b"\x00" * padding

    @classmethod
    def from_buffer(cls, buf: bytes, offset: int = 0) -> "NetlinkMessage":
        nlmsg = type(Structure).from_buffer(cls, buf, offset)
        if nlmsg.nlmsg_len > len(buf):
            raise ValueError("Buffer too small for nlmsg_len")

        payload_class = cls._nlmsg_type_map.get(nlmsg._nlmsg_type)
        payload_offset = offset + sizeof(cls)

        if payload_class:
            nlmsg._payload = payload_class.from_buffer(buf, offset=payload_offset)
        else:
            nlmsg._payload = buf[payload_offset:payload_offset + nlmsg.nlmsg_len]
        return nlmsg

    @classmethod
    def from_buffer_copy(cls, buf: bytes, offset: int = 0) -> "NetlinkMessage":
        nlmsg = type(Structure).from_buffer_copy(cls, buf, offset)
        if nlmsg.nlmsg_len > len(buf):
            raise ValueError("Buffer too small for nlmsg_len")

        payload_class = cls._nlmsg_type_map.get(nlmsg._nlmsg_type)
        payload_offset = offset + sizeof(cls)

        if payload_class:
            nlmsg._payload = payload_class.from_buffer_copy(buf, offset=payload_offset)
        else:
            nlmsg._payload = buf[payload_offset:payload_offset + nlmsg.nlmsg_len]
        return nlmsg

    @property
    def payload(self) -> RTNetlinkMessage | bytes:
        return self._payload

    @payload.setter
    def payload(self, payload: RTNetlinkMessage | bytes):
        self._payload = payload
        self.nlmsg_len = sizeof(self) + len(payload)

    @property
    def aligned_nlmsg_len(self) -> int:
        return nlmsg_space(self.nlmsg_len)

    @property
    def nlmsg_type(self) -> NetlinkMessageType:
        return NetlinkMessageType(self._nlmsg_type)

    @nlmsg_type.setter
    def nlmsg_type(self, value: NetlinkMessageType):
        self._nlmsg_type = value

    @property
    def nlmsg_flags(self) -> NetlinkMessageFlags:
        return NetlinkMessageFlags(self._nlmsg_flags)

    @nlmsg_flags.setter
    def nlmsg_flags(self, value: NetlinkMessageFlags):
        self._nlmsg_flags = value
