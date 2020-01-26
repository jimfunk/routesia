"""
routesia/interface/address/entity.py - Address entity
"""

import errno
from ipaddress import ip_interface
from pyroute2 import NetlinkError

from routesia.entity import Entity
from routesia.interface.address.address_pb2 import Address


class AddressEntity(Entity):
    def __init__(self, ifname, iproute, config=None, event=None):
        super().__init__(config=config)
        self.ifname = ifname
        self.iproute = iproute
        self.state = Address()
        self.ifindex = None
        if event:
            self.ifindex = event.ifindex
            self.update_state(event)
            print("New address %s on %s. Config: %s" % (event.ip, event.ifname, self.config))

    def update_state(self, event):
        self.state.ip = str(event.ip)
        self.state.label = event.attrs.get('IFA_LABEL', '')
        self.apply()

    def set_ifindex(self, ifindex):
        self.ifindex = ifindex
        self.apply()

    def handle_remove(self):
        self.state.Clear()
        self.apply()

    def update_config(self, config):
        self.config = config
        self.apply()

    def addr(self, *args, **kwargs):
        kwargs['index'] = self.ifindex
        if 'add' in args:
            kwargs['proto'] = self.iproute.rt_proto
        try:
            return self.iproute.iproute.addr(*args, **kwargs)
        except NetlinkError as e:
            if e.code != errno.EEXIST:
                raise

    def apply(self):
        if self.config is not None and self.ifindex is not None:
            print(self.state)
            if not self.state.ip:
                ip = ip_interface(self.config.ip)
                self.addr('add', address=str(ip.ip), mask=ip.network.prefixlen)
