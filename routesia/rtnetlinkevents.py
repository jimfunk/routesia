"""
Netlink events
"""

from dataclasses import dataclass
from ipaddress import ip_interface, ip_network
import socket

from routesia.event import Event


class IgnoreMessage(Exception):
    pass


class RtnetlinkEvent(Event):
    def __init__(self, iproute, message):
        self.message = message
        self.attrs = dict(message["attrs"])


class AddressEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)
        self.ifindex = message["index"]
        self.ifname = iproute.get_interface_name_by_index(self.ifindex)
        self.peer = None
        if "IFA_LOCAL" in self.attrs:
            self.ip = ip_interface(
                "%s/%s" % (self.attrs["IFA_LOCAL"], message["prefixlen"])
            )
            if self.attrs["IFA_LOCAL"] != self.attrs["IFA_ADDRESS"]:
                self.peer = ip_interface(
                    "%s/%s" % (self.attrs["IFA_ADDRESS"], message["prefixlen"])
                )
        else:
            self.ip = ip_interface(
                "%s/%s" % (self.attrs["IFA_ADDRESS"], message["prefixlen"])
            )
        self.scope = message['scope']


class AddressAddEvent(AddressEvent):
    pass


class AddressRemoveEvent(AddressEvent):
    pass


class RouteEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)
        if message["family"] not in (socket.AF_INET, socket.AF_INET6):
            raise IgnoreMessage
        if "RTA_DST" in self.attrs:
            self.destination = ip_network(
                "%s/%s" % (self.attrs["RTA_DST"], message["dst_len"])
            )
        else:
            if message["family"] == socket.AF_INET:
                self.destination = ip_network("0.0.0.0/%s" % message["dst_len"])
            else:
                self.destination = ip_network("::/%s" % message["dst_len"])


class RouteAddEvent(RouteEvent):
    pass


class RouteRemoveEvent(RouteEvent):
    pass


class NeighbourEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)


class NeighbourAddEvent(NeighbourEvent):
    pass


class NeighbourRemoveEvent(NeighbourEvent):
    pass
