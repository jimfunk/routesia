import socket

from routesia.netlink.rtnetlink.interface import InterfaceInfoMessage
from routesia.netlink.rtnetlink.message import RTAttribute, RTNetlinkMessage
from routesia.netlink.message import NetlinkMessage, NetlinkMessageType
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

    msg = NetlinkMessage(
        nlmsg_len=16,
        nlmsg_type=NetlinkMessageType.RTM_GETLINK,
        nlmsg_flags=0,
        nlmsg_seq=1,
        nlmsg_pid=0,
    )
    writer.write(
        InterfaceInfoMessage(

        )
    )

    response = await reader.read()
    assert isinstance(response, RTNetlinkMessage)
    assert response.nlmsg_type == NetlinkMessageType.RTM_NEWLINK

    writer.close()


async def test_netlink_receive_error(netns):
    """
    Test that the connection handles error messages.
    """
    reader, writer = await open_netlink_connection(proto=socket.NETLINK_ROUTE)

    # Create a netlink error message
    error_msg = NetlinkMessage(
        nlmsg_len=16,
        nlmsg_type=NetlinkMessageType.NLMSG_ERROR,
        nlmsg_flags=0,
        nlmsg_seq=1,
        nlmsg_pid=0,
    )

    # Send it manually
    sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE)
    sock.bind((0, 0))
    sock.send(error_msg.pack())

    # Read the error msg
    msg = await reader.read()
    assert isinstance(msg, NetlinkMessage)
    assert msg.nlmsg_type == NetlinkMessageType.NLMSG_ERROR

    writer.close()
    sock.close()
