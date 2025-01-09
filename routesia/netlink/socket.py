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

            self.recv_queue.put_nowait(message.downcast())


class NetlinkStreamReader:
    def __init__(self, protocol: NetlinkProtocol):
        self.protocol = protocol

    async def read(self) -> NetlinkMessage:
        message = await self.protocol.recv_queue.get()
        if isinstance(message, Exception):
            raise message
        return message


class NetlinkStreamWriter:
    def __init__(self, protocol: NetlinkProtocol, transport: asyncio.BaseTransport):
        self._protocol = protocol
        self._transport = transport
        self._sequence = 0

    def write(self, msg_type: int, data: bytes, flags: int = 0):
        """Write a Netlink message."""
        self._sequence += 1
        message = NetlinkMessage(
            type=msg_type,
            flags=flags,
            sequence=self._sequence,
            pid=0,  # kernel sets this
            data=data,
        )
        self._transport.write(message.pack())

    def close(self):
        """Close the writer."""
        self._transport.close()


async def open_netlink_connection(
    protocol: int = socket.NETLINK_ROUTE,
    groups: int = 0,
) -> tuple[NetlinkStreamReader, NetlinkStreamWriter]:
    """
    Open a netlink connection and return a tuple of NetlinkStreamReader and
    NetlinkStreamWriter.
    """
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, protocol)
    sock.bind((0, groups))

    protocol = NetlinkProtocol()
    transport = await loop.create_connection(lambda: protocol, sock=sock)

    await protocol._connected

    reader = NetlinkStreamReader(protocol)
    writer = NetlinkStreamWriter(protocol, transport[0])

    return reader, writer


# Example usage:
async def main():
    reader, writer = await open_netlink_connection()

    # Send a RTM_GETLINK message to get network interface info
    RTM_GETLINK = 18
    NLM_F_REQUEST = 1
    NLM_F_DUMP = 0x300

    # Create message payload (empty for RTM_GETLINK dump request)
    writer.write(RTM_GETLINK, b"", flags=NLM_F_REQUEST | NLM_F_DUMP)

    try:
        while True:
            msg = await reader.read()
            print(f"Received message: type={msg.type} seq={msg.sequence}")
            # Process message...

    except Exception as e:
        print(f"Error: {e}")
    finally:
        writer.close()


if __name__ == "__main__":
    asyncio.run(main())
