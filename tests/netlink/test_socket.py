import socket

import pytest

from routesia.netlink.exceptions import NetlinkError
from routesia.netlink.rtnetlink.link import InterfaceInfoMessage
from routesia.netlink.rtnetlink.attribute import RTAttribute
from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageType,
    NetlinkMessageFlags,
    NetlinkErrorMessage,
)
from routesia.netlink.socket import (
    NetlinkStreamReader,
    NetlinkStreamWriter,
    NetlinkProtocol,
    open_netlink_connection,
)


async def test_netlink_connection(netns):
    """
    Test communication with netlink connection.
    """
    reader, writer = await open_netlink_connection()

    assert isinstance(reader, NetlinkStreamReader)
    assert isinstance(writer, NetlinkStreamWriter)

    # Use RTM_GETLINK for interface index 1 (lo)
    msg = NetlinkMessage(
        nlmsg_type=NetlinkMessageType.RTM_GETLINK,
        nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST,
        payload=InterfaceInfoMessage(ifi_index=1),
    )
    writer.write(msg)

    response = await reader.read()
    assert isinstance(response, NetlinkMessage)
    assert response.nlmsg_type == NetlinkMessageType.RTM_NEWLINK

    writer.close()


async def test_netlink_receive_error(netns):
    """
    Test that the connection handles error messages.
    """
    reader, writer = await open_netlink_connection(proto=socket.NETLINK_ROUTE)
    pid, _ = writer.transport.get_extra_info("sockname")

    # Create a netlink error message
    error_msg = NetlinkMessage(
        nlmsg_len=16,
        nlmsg_type=NetlinkMessageType.NLMSG_ERROR,
        nlmsg_flags=0,
        nlmsg_seq=1,
        nlmsg_pid=pid,  # Send to the reader
        payload=NetlinkErrorMessage(error=-22),  # EINVAL
    )

    # Send it manually
    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE)
    sock.bind((0, 0))
    sock.sendto(bytes(error_msg), (pid, 0))

    # Read the error msg
    msg = await reader.read()
    assert isinstance(msg, NetlinkMessage)
    assert msg.nlmsg_type == NetlinkMessageType.NLMSG_ERROR

    writer.close()
    sock.close()
