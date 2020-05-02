"""
routesia/interface/address/entity.py - Address entity
"""

import errno
from ipaddress import ip_interface
from pyroute2 import NetlinkError

from routesia.entity import Entity
from routesia.address import address_pb2


class AddressEntity(Entity):
    def __init__(self, ifname, iproute, ifindex=None, config=None):
        super().__init__()
        self.config = config
        self.ifname = ifname
        self.iproute = iproute
        self.ifname = ifname
        self.state = address_pb2.Address()
        self.set_ifindex(ifindex)
        self.state.address.interface = self.ifname
        self.apply()

    def update_state(self, event):
        self.state.address.ip = str(event.ip)
        self.state.address.peer = str(event.peer.ip) if event.peer else ""
        self.state.address.scope = event.scope
        self.ifindex = event.ifindex
        if self.ifindex:
            self.state.state = address_pb2.Address.PRESENT
        else:
            self.state.state = address_pb2.Address.INTERFACE_MISSING
        self.apply()

    def set_ifindex(self, ifindex):
        self.ifindex = ifindex
        self.apply()

    def handle_remove(self):
        self.apply()

    def on_config_removed(self):
        self.config = None
        self.remove()

    def on_config_change(self, config):
        self.config = config
        self.apply()

    def update_config(self, config):
        self.config = config
        self.apply()

    def addr(self, *args, **kwargs):
        kwargs["index"] = self.ifindex
        if "add" in args:
            kwargs["proto"] = self.iproute.rt_proto
        try:
            return self.iproute.iproute.addr(*args, **kwargs)
        except NetlinkError as e:
            if e.code != errno.EEXIST:
                raise

    def apply(self):
        if self.ifindex is None:
            self.state.state = address_pb2.Address.INTERFACE_MISSING
        else:
            self.state.state = address_pb2.Address.PRESENT
            if self.config is not None:
                if (
                    self.state.address.SerializeToString()
                    != self.config.SerializeToString()
                ):
                    self.remove()
                    ip = ip_interface(self.config.ip)
                    args = {}
                    if self.config.peer:
                        peer = ip_interface(self.config.peer)
                        args["address"] = str(peer.ip)
                        args["local"] = str(ip.ip)
                    else:
                        args["address"] = str(ip.ip)
                    self.addr(
                        "add", index=self.ifindex, mask=ip.network.prefixlen, **args
                    )

    def remove(self):
        if self.state.address.ip:
            ip = ip_interface(self.state.address.ip)
            print(
                "index: %s, address: %s, mask: %s"
                % (self.ifindex, str(ip.ip), ip.network.prefixlen)
            )
            self.addr(
                "remove",
                index=self.ifindex,
                address=str(ip.ip),
                mask=ip.network.prefixlen,
            )

    def to_message(self, message):
        "Set message parameters from entity state"
        message.CopyFrom(self.state)
