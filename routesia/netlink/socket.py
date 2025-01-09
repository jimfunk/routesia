import asyncio
from ctypes import sizeof
import socket

from routesia.netlink.message import NetlinkMessage, nlmsg_space


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

    def data_received(self, data):
        self.buffer += data
        while len(self.buffer) >= sizeof(NetlinkMessage):
            msg = NetlinkMessage.from_buffer(self.buffer)
            space = nlmsg_space(msg.nlmsg_len)
            if len(self.buffer) < space:
                break

            message = NetlinkMessage.from_buffer_copy(self.buffer)
            self.buffer = self.buffer[space:]

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
    def __init__(self, protocol: NetlinkProtocol, transport: asyncio.BaseTransport):
        self.protocol = protocol
        self.transport = transport
        self.seq = 0

    def write(self, msg: NetlinkMessage):
        """
        Write a Netlink message
        """
        self.seq += 1
        msg.nlmsg_seq = self.seq
        self.transport.write(bytes(msg))

    def close(self):
        """
        Close the writer
        """
        self.transport.close()


async def open_netlink_connection(
    proto: int = socket.NETLINK_ROUTE,
    groups: int = 0,
) -> tuple[NetlinkStreamReader, NetlinkStreamWriter]:
    """
    Open a netlink connection and return a tuple of NetlinkStreamReader and
    NetlinkStreamWriter.
    """
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, proto)
    sock.bind((0, groups))

    protocol = NetlinkProtocol()
    transport = await loop.create_connection(lambda: protocol, sock=sock)

    await protocol.connected

    reader = NetlinkStreamReader(protocol)
    writer = NetlinkStreamWriter(protocol, transport[0])

    return reader, writer
