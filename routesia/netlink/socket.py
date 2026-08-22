import asyncio
from ctypes import c_uint32
import socket

from routesia.netlink.constants import (
    SOL_NETLINK,
    NETLINK_EXT_ACK,
    NETLINK_GET_STRICT_CHK,
)
from routesia.netlink.exceptions import NetlinkError
from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageFlags,
    NetlinkMessageType,
    NetlinkGroup,
)
from routesia.netlink.rtnetlink.link.operations import LinkOperations
from routesia.netlink.rtnetlink.address.operations import AddressOperations
from routesia.netlink.rtnetlink.neighbor.operations import NeighborOperations
from routesia.netlink.rtnetlink.rule.operations import RuleOperations


class NetlinkProtocol(asyncio.Protocol):
    def __init__(self):
        self.transport = None
        self.buffer = b""
        self.connected = asyncio.Future()
        self.recv_queue = asyncio.Queue()

    def connection_made(self, transport):
        self.transport = transport
        if not self.connected.done():
            self.connected.set_result(None)

    def connection_lost(self, exc):
        if exc:
            self.recv_queue.put_nowait(exc)

    def datagram_received(self, data, addr=None):
        self.buffer += data
        while len(self.buffer) >= NetlinkMessage._fixed_size:
            nlmsg_len = c_uint32.from_buffer_copy(self.buffer)
            if len(self.buffer) < nlmsg_len.value:
                break

            message = NetlinkMessage.from_buffer(self.buffer)
            self.buffer = self.buffer[nlmsg_len.value :]

            self.recv_queue.put_nowait(message)


class NetlinkStreamReader:
    def __init__(self, protocol: NetlinkProtocol):
        self.protocol = protocol

    async def read(self) -> NetlinkMessage:
        """
        Read a message from the netlink socket
        """
        message = await self.protocol.recv_queue.get()
        if isinstance(message, Exception):
            raise message
        return message


class NetlinkStreamWriter:
    def __init__(self, protocol: NetlinkProtocol, transport: asyncio.DatagramTransport):
        self.protocol = protocol
        self.transport = transport
        self.seq = 0

    def write(self, msg: NetlinkMessage):
        """
        Write a Netlink message
        """
        self.seq += 1
        msg.nlmsg_seq = self.seq
        self.transport.sendto(bytes(msg))

    def close(self):
        """
        Close the writer
        """
        self.transport.close()


async def open_netlink_connection(
    proto: int = socket.NETLINK_ROUTE,
    groups: NetlinkGroup = NetlinkGroup.NONE,
) -> tuple[NetlinkStreamReader, NetlinkStreamWriter]:
    """
    Open a netlink connection and return a tuple of NetlinkStreamReader and
    NetlinkStreamWriter.
    """
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, proto)
    sock.bind((0, groups))
    sock.setsockopt(SOL_NETLINK, NETLINK_EXT_ACK, 1)
    sock.setsockopt(SOL_NETLINK, NETLINK_GET_STRICT_CHK, 1)

    protocol = NetlinkProtocol()
    transport = await loop.create_datagram_endpoint(lambda: protocol, sock=sock)

    await protocol.connected

    reader = NetlinkStreamReader(protocol)
    writer = NetlinkStreamWriter(protocol, transport[0])

    return reader, writer


class NetlinkSocket:
    def __init__(
        self,
        proto: int = socket.NETLINK_ROUTE,
        groups: NetlinkGroup = NetlinkGroup.NONE,
    ):
        self.proto = proto
        self.groups = groups
        self.reader = None
        self.writer = None
        self.link = LinkOperations(self)
        self.address = AddressOperations(self)
        self.neighbor = NeighborOperations(self)
        self.rule = RuleOperations(self)

    async def __aenter__(self):
        self.reader, self.writer = await open_netlink_connection(
            proto=self.proto, groups=self.groups
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.writer:
            self.writer.close()

    async def read(self) -> NetlinkMessage:
        if not self.reader:
            raise RuntimeError("Socket not open")
        return await self.reader.read()

    async def request(self, msg: NetlinkMessage) -> list[NetlinkMessage]:
        if not self.writer:
            raise RuntimeError("Socket not open")
        self.writer.write(msg)
        responses = []
        while True:
            resp = await self.reader.read()
            if resp.nlmsg_type == NetlinkMessageType.NLMSG_ERROR:
                err = resp.error
                if err.is_ack:
                    # This is an ACK
                    break
                raise NetlinkError(err.error, err)
            if resp.nlmsg_type == NetlinkMessageType.NLMSG_DONE:
                break
            responses.append(resp)
            if not (resp.nlmsg_flags & NetlinkMessageFlags.NLM_F_MULTI):
                break
        return responses
