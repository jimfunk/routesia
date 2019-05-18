"""
routesia/interface/address/address.py - Interface address support
"""

import errno
from ipaddress import ip_interface
from pyroute2 import NetlinkError

from routesia.config import ConfigProvider
from routesia.entity import Entity
from routesia.injector import Provider
from routesia.interface.address.address_pb2 import Address
from routesia.server import Server
from routesia.rtnetlink.iproute import (
    IPRouteProvider,
    AddressAddEvent,
    AddressRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)


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


class AddressProvider(Provider):
    def __init__(self, server: Server, iproute: IPRouteProvider, config: ConfigProvider):
        self.server = server
        self.iproute = iproute
        self.config = config

        # Indexed by (ifname, ip)
        self.addresses = {}

        # Track interfaces for use by configured addresses
        self.interfaces = {}

        self.server.subscribe_event(AddressAddEvent, self.handle_address_add)
        self.server.subscribe_event(AddressRemoveEvent, self.handle_address_remove)
        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

    def handle_config_update(self, old, new):
        pass

    def find_config(self, address_event):
        interface_config = self.config.data.interface
        for field, _ in interface_config.ListFields():
            for interface in getattr(interface_config, field.name):
                if interface.name == address_event.ifname:
                    for address in interface.address:
                        if address.ip == address_event.ip:
                            return address
                    return

    def handle_address_add(self, address_event):
        ifname = address_event.ifname
        ip = str(address_event.ip)

        if (ifname, ip) not in self.addresses:
            config = self.find_config(address_event)
            address = AddressEntity(ifname, self.iproute, config, address_event)
            self.addresses[(ifname, ip)] = address
        else:
            address = self.addresses[(ifname, ip)]
            address.update_state(address_event)

    def handle_address_remove(self, address_event):
        ifname = address_event.ifname
        ip = str(address_event.ip)

        if (ifname, ip) in self.addresses:
            address = self.addresses[(ifname, ip)]
            address.handle_remove()
            if address.config is None:
                del self.addresses[(ifname, ip)]

    def handle_interface_add(self, interface_event):
        self.interfaces[interface_event.ifname] = interface_event
        for address in self.addresses.values():
            if address.ifname == interface_event.ifname:
                address.set_ifindex(interface_event.ifindex)

    def handle_interface_remove(self, interface_event):
        for address in self.address.values():
            if address.ifname == interface_event.ifname:
                address.set_ifindex(None)
        if interface_event.ifname in self.interfaces:
            del self.interfaces[interface_event.ifname]

    def startup(self):
        interface_config = self.config.data.interface
        for field, _ in interface_config.ListFields():
            for interface in getattr(interface_config, field.name):
                for config in interface.address:
                    if (interface.name, config.ip) not in self.addresses:
                        self.addresses[(interface.name, config.ip)] = AddressEntity(interface.name, self.iproute, config=config, event=self.interfaces.get(interface.name, None))
