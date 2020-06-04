"""
routesia/interface/address/provider.py - Interface address support
"""

import errno
from ipaddress import ip_interface
from pyroute2.netlink.exceptions import NetlinkError

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.address import address_pb2
from routesia.address.entity import AddressEntity
from routesia.exceptions import RPCInvalidParameters, RPCEntityExists
from routesia.rpc.provider import RPCProvider
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.rtnetlink.events import (
    AddressAddEvent,
    AddressRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)
from routesia.server import Server


class AddressProvider(Provider):
    def __init__(
        self,
        server: Server,
        iproute: IPRouteProvider,
        config: ConfigProvider,
        rpc: RPCProvider,
    ):
        self.server = server
        self.iproute = iproute
        self.config = config
        self.rpc = rpc

        # Indexed by (ifname, ip)
        self.addresses = {}

        # Track interfaces for use by configured addresses
        self.interfaces = {}

        self.server.subscribe_event(AddressAddEvent, self.handle_address_add)
        self.server.subscribe_event(AddressRemoveEvent, self.handle_address_remove)
        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

    def on_config_change(self, config):
        new_addresses = {}
        for address in self.config.data.addresses.address:
            new_addresses[(address.interface, address.ip)] = address
        new_address_keys = set(new_addresses.keys())

        # Remove addresses that no longer have a config
        for key, address in list(self.addresses.items()):
            if address.config and key not in new_address_keys:
                address.on_config_removed()

        # Add/update the rest
        for key in new_address_keys:
            if key in self.addresses:
                self.addresses[key].on_config_change(new_addresses[key])
            else:
                config = new_addresses[key]
                if config.interface in self.interfaces:
                    ifindex = self.interfaces[config.interface].ifindex
                else:
                    ifindex = None
                self.addresses[key] = AddressEntity(
                    config.interface, self.iproute, ifindex, config=config
                )

    def find_config(self, address_event):
        for config in self.config.data.addresses.address:
            if (
                config.interface == address_event.ifname
                and config.ip == address_event.ip
            ):
                return config

    def handle_address_add(self, address_event):
        ifname = address_event.ifname
        ip = str(address_event.ip)

        if (ifname, ip) not in self.addresses:
            config = self.find_config(address_event)
            address = AddressEntity(ifname, self.iproute, config)
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
        for address in self.addresses.values():
            if address.ifname == interface_event.ifname:
                address.set_ifindex(None)
        if interface_event.ifname in self.interfaces:
            del self.interfaces[interface_event.ifname]

    def add_dynamic_address(self, interface, address):
        """
        Add a dynamic address. Note that a prefix route will NOT be added. The
        caller is responsible for handling it
        """
        key = (interface, str(address))
        if key not in self.addresses:
            if interface in self.interfaces:
                ifindex = self.interfaces[interface].ifindex
            else:
                ifindex = None

            print("Adding dynamic address %s to %s" % (address, interface))
            self.addresses[key] = AddressEntity(
                interface,
                self.iproute,
                ifindex,
                dynamic=ip_interface(address),
            )

    def remove_dynamic_address(self, interface, address):
        key = (interface, str(address))
        if key in self.addresses:
            print("Removing dynamic address %s to %s" % (address, interface))
            self.addresses[key].remove_dynamic()

    def load(self):
        self.config.register_change_handler(self.on_config_change)

    def startup(self):
        self.rpc.register("/address/list", self.rpc_list_addresses)
        self.rpc.register("/address/config/list", self.rpc_list_address_configs)
        self.rpc.register("/address/config/add", self.rpc_add_address)
        self.rpc.register("/address/config/update", self.rpc_update_address)
        self.rpc.register("/address/config/delete", self.rpc_delete_address)
        for config in self.config.data.addresses.address:
            if (config.interface, config.ip) not in self.addresses:
                if config.interface in self.interfaces:
                    ifindex = self.interfaces[config.interface].ifindex
                else:
                    ifindex = None
                self.addresses[(config.interface, config.ip)] = AddressEntity(
                    config.interface, self.iproute, ifindex=ifindex, config=config,
                )

    def rpc_list_addresses(self, msg: None) -> address_pb2.AddressList:
        addresses = address_pb2.AddressList()
        for entity in self.addresses.values():
            address = addresses.address.add()
            entity.to_message(address)
        return addresses

    def rpc_list_address_configs(self, msg: None) -> address_pb2.AddressConfigList:
        return self.config.staged_data.addresses

    def validate_interface_and_ip(self, msg: address_pb2.AddressConfig):
        if not msg.interface:
            raise RPCInvalidParameters("interface not specified")
        if not msg.ip:
            raise RPCInvalidParameters("ip not specified")
        try:
            ip_interface(msg.ip)
        except ValueError:
            raise RPCInvalidParameters("ip not an IP address")

    def rpc_add_address(self, msg: address_pb2.AddressConfig) -> None:
        self.validate_interface_and_ip(msg)

        for address in self.config.staged_data.addresses.address:
            if address.interface == msg.interface and ip_interface(
                address.ip
            ) == ip_interface(msg.ip):
                raise RPCEntityExists("%s %s" % (msg.interface, msg.ip))
        address = self.config.staged_data.addresses.address.add()
        address.CopyFrom(msg)
        return address

    def rpc_update_address(self, msg: address_pb2.AddressConfig) -> None:
        self.validate_interface_and_ip(msg)

        for address in self.config.staged_data.addresses.address:
            if address.interface == msg.interface and ip_interface(
                address.ip
            ) == ip_interface(msg.ip):
                address.CopyFrom(msg)

    def rpc_delete_address(self, msg: address_pb2.AddressConfig) -> None:
        self.validate_interface_and_ip(msg)

        for i, address in enumerate(self.config.staged_data.addresses.address):
            if address.interface == msg.interface and ip_interface(
                address.ip
            ) == ip_interface(msg.ip):
                del self.config.staged_data.addresses.address[i]
