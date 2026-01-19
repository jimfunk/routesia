"""
Netlink provider
"""

from dataclasses import dataclass
import logging

from routesia.netlink.message import NetlinkMessageType, NetlinkGroup, NetlinkMessage
from routesia.netlink.rtnetlink.link import (
    InterfaceInfoMessage,
    InterfaceOperationalState,
)
from routesia.netlink.socket import NetlinkSocket
from routesia.service import Provider, Event, Service


logger = logging.getLogger("netlink")


@dataclass(slots=True)
class NetlinkLinkAddEvent(Event):
    name: str
    type: int
    index: int
    flags: int
    state: InterfaceOperationalState
    message: InterfaceInfoMessage


@dataclass(slots=True)
class NetlinkLinkDeleteEvent(Event):
    name: str
    type: int
    index: int
    message: InterfaceInfoMessage


class RtnetlinkProvider(Provider):
    """
    Handles the interface with rtnetlink.

    Detects changes from the kernel side and publishes them as events.
    """

    def __init__(self, service: Service):
        self.service = service

    async def main(self):
        """
        Main loop for receiving netlink events.
        """
        async with NetlinkSocket(
            groups=NetlinkGroup.RTMGRP_LINK
            | NetlinkGroup.RTMGRP_IPV4_IFADDR
            | NetlinkGroup.RTMGRP_IPV6_IFADDR
            | NetlinkGroup.RTMGRP_IPV4_ROUTE
            | NetlinkGroup.RTMGRP_IPV6_ROUTE
            | NetlinkGroup.RTMGRP_NEIGH
        ) as netlink:
            while True:
                msg = await netlink.read()
                self.handle_message(msg)

    def handle_message(self, msg: NetlinkMessage):
        if msg.nlmsg_type == NetlinkMessageType.RTM_NEWLINK:
            self._handle_RTM_NEWLINK(msg.payload)
        elif msg.nlmsg_type == NetlinkMessageType.RTM_DELLINK:
            self._handle_RTM_DELLINK(msg.payload)

    def _handle_RTM_NEWLINK(self, message: InterfaceInfoMessage):
        self.service.publish_event(
            NetlinkLinkAddEvent(
                name=message.ifname,
                type=message.ifi_type,
                index=message.ifi_index,
                flags=message.ifi_flags,
                state=message.operstate or InterfaceOperationalState.IF_OPER_UNKNOWN,
                message=message,
            )
        )

    def _handle_RTM_DELLINK(self, message: InterfaceInfoMessage):
        self.service.publish_event(
            NetlinkLinkDeleteEvent(
                name=message.ifname,
                type=message.ifi_type,
                index=message.ifi_index,
                message=message,
            )
        )
