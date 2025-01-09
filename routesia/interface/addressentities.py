"""
routesia/interface/address/entity.py - Address entity
"""

import errno
from ipaddress import ip_interface
from pyroute2 import NetlinkError
from pyroute2.netlink.rtnl.ifaddrmsg import IFA_F_NOPREFIXROUTE

from routesia.dhcp.dhcpclientevents import DHCPv4LeaseAcquired
from routesia.netlinkevents import AddressAddEvent
from routesia.schema.v2 import address_pb2


class AddressEntity:
    def __init__(self, ifname, iproute, ifindex=None, config=None):
        super().__init__()
        self.ifname = ifname
        self.iproute = iproute
        self.config = config
        self.status = address_pb2.Address()
        self.set_ifindex(ifindex)
        self.status.address.interface = self.ifname
        self.apply()

    def handle_add(self, event: AddressAddEvent):
        self.status.address.ip = str(event.ip)
        self.status.address.peer = str(event.peer.ip) if event.peer else ""
        self.status.address.scope = event.scope
        self.status.state = address_pb2.Address.PRESENT

    def set_ifindex(self, ifindex):
        self.ifindex = ifindex
        self.apply()

    def handle_remove(self):
        self.status.state = address_pb2.Address.ADDRESS_MISSING
        self.apply()

    def on_config_removed(self):
        self.config = None
        self.remove()

    def handle_config_change(self, config):
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

    def get_params(self):
        if self.ifindex is None:
            return None

        ip = ip_interface(self.config.ip)
        args = {
            "index": self.ifindex,
            "prefixlen": ip.network.prefixlen,
        }
        if self.config.peer:
            peer = ip_interface(self.config.peer)
            args["address"] = str(peer.ip)
            args["local"] = str(ip.ip)
        else:
            args["address"] = str(ip.ip)

        return args

    def apply(self):
        if not self.config:
            return

        if self.ifindex is None:
            self.status.state = address_pb2.Address.INTERFACE_MISSING
        else:
            self.status.state = address_pb2.Address.ADDRESS_MISSING
            if (
                self.status.address.SerializeToString()
                != self.config.SerializeToString()
            ):
                self.remove()
                try:
                    self.addr("add", **self.get_params())
                except NetlinkError as e:
                    if e.code == errno.ENODEV:
                        self.set_ifindex(None)

    def remove(self):
        if self.status.address.ip:
            ip = ip_interface(self.status.address.ip)
            self.addr(
                "remove",
                index=self.ifindex,
                address=str(ip.ip),
                prefixlen=ip.network.prefixlen,
            )

    def remove_dynamic(self):
        self.dynamic = None
        self.remove()

    def to_message(self, message):
        "Set message parameters from entity state"
        message.CopyFrom(self.status)


class DHCPAddressEntity(AddressEntity):
    def __init__(self, lease: DHCPv4LeaseAcquired, iproute, ifindex=None):
        self.lease = lease
        super().__init__(lease.interface, iproute, ifindex)

    def get_params(self):
        if self.ifindex is None:
            return None

        return {
            "index": self.ifindex,
            "prefixlen": self.lease.address.network.prefixlen,
            "address": str(self.lease.address.ip),
            "flags": IFA_F_NOPREFIXROUTE,
        }

    def apply(self):
        if self.ifindex is None:
            self.status.state = address_pb2.Address.INTERFACE_MISSING
        else:
            self.status.state = address_pb2.Address.ADDRESS_MISSING
            try:
                self.addr("add", **self.get_params())
            except NetlinkError as e:
                if e.code == errno.ENODEV:
                    self.set_ifindex(None)

    def handle_dhcp_lease_acquired(self, lease: DHCPv4LeaseAcquired):
        if self.lease.address != lease.address:
            self.remove()
            self.lease = lease
            self.apply()
