"""
routesia/interface/address/provider.py - Interface address support
"""

from ipaddress import ip_interface, IPv4Interface, IPv6Interface
import logging

from routesia.address.entity import AddressEntity, DHCPAddressEntity
from routesia.config.provider import ConfigProvider
from routesia.dhcp.client.events import DHCPv4LeaseAcquired, DHCPv4LeaseLost, DHCPv4LeasePreinit
from routesia.service import Provider
from routesia.rpc import RPC, RPCInvalidArgument
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.rtnetlink.events import (
    AddressAddEvent,
    AddressRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)
from routesia.schema.v1 import address_pb2
from routesia.service import Service


logger = logging.getLogger("address")


class AddressProvider(Provider):
    def __init__(
        self,
        service: Service,
        iproute: IPRouteProvider,
        config: ConfigProvider,
        rpc: RPC,
    ):
        self.service = service
        self.iproute = iproute
        self.config = config
        self.rpc = rpc

        # Indexed by (ifname, ip)
        self.addresses = {}

        # Track interfaces for use by configured addresses
        self.interfaces: dict[tuple[IPv4Interface | IPv6Interface], AddressEntity] = {}

        self.dhcp_addresses: dict[str, DHCPAddressEntity] = {}

        self.config.register_change_handler(self.on_config_change)

        self.service.subscribe_event(AddressAddEvent, self.handle_address_add)
        self.service.subscribe_event(AddressRemoveEvent, self.handle_address_remove)
        self.service.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.service.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)
        self.service.subscribe_event(DHCPv4LeasePreinit, self.handle_dhcp_lease_preinit)
        self.service.subscribe_event(DHCPv4LeaseAcquired, self.handle_dhcp_lease_acquired)
        self.service.subscribe_event(DHCPv4LeaseLost, self.handle_dhcp_lease_lost)

        self.rpc.register("address/list", self.rpc_list_addresses)
        self.rpc.register("address/config/list", self.rpc_list_address_configs)
        self.rpc.register("address/config/add", self.rpc_add_address)
        self.rpc.register("address/config/update", self.rpc_update_address)
        self.rpc.register("address/config/delete", self.rpc_delete_address)

    def on_config_change(self, config):
        new_addresses = {}
        for address in config.addresses.address:
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

    async def handle_address_add(self, address_event):
        ifname = address_event.ifname
        ip = str(address_event.ip)

        if (ifname, ip) not in self.addresses:
            config = self.find_config(address_event)
            address = AddressEntity(ifname, self.iproute, config)
            self.addresses[(ifname, ip)] = address
        else:
            address = self.addresses[(ifname, ip)]
        address.handle_add(address_event)

    async def handle_address_remove(self, address_event):
        ifname = address_event.ifname
        ip = str(address_event.ip)

        if (ifname, ip) in self.addresses:
            address = self.addresses[(ifname, ip)]
            address.handle_remove()
            if address.config is None:
                del self.addresses[(ifname, ip)]

    async def handle_interface_add(self, interface_event):
        self.interfaces[interface_event.ifname] = interface_event
        for address in self.addresses.values():
            if address.ifname == interface_event.ifname:
                address.set_ifindex(interface_event.ifindex)

    async def handle_interface_remove(self, interface_event):
        for address in self.addresses.values():
            if address.ifname == interface_event.ifname:
                address.set_ifindex(None)
        if interface_event.ifname in self.interfaces:
            del self.interfaces[interface_event.ifname]

    async def handle_dhcp_lease_preinit(self, event: DHCPv4LeasePreinit):
        if event.address:
            address = self.addresses.get((event.interface, event.address), None)
            if address:
                address.remove_dynamic()

    async def handle_dhcp_lease_acquired(self, event: DHCPv4LeaseAcquired):
        if event.interface in self.dhcp_addresses:
            self.dhcp_addresses[event.interface].handle_dhcp_lease_acquired(event)
        else:
            if event.interface in self.interfaces:
                ifindex = self.interfaces[event.interface].ifindex
            else:
                ifindex = None
            logger.debug(f"Adding DHCP entity for {event.interface}")
            self.dhcp_addresses[event.interface] = DHCPAddressEntity(event, self.iproute, ifindex)

    async def handle_dhcp_lease_lost(self, event: DHCPv4LeaseLost):
        if event.interface in self.dhcp_addresses:
            self.dhcp_addresses[event.interface].remove()
            del self.dhcp_addresses[event.interface]

    def start(self):
        for config in self.config.data.addresses.address:
            if (config.interface, config.ip) not in self.addresses:
                if config.interface in self.interfaces:
                    ifindex = self.interfaces[config.interface].ifindex
                else:
                    ifindex = None
                self.addresses[(config.interface, config.ip)] = AddressEntity(
                    config.interface, self.iproute, ifindex=ifindex, config=config,
                )

    async def rpc_list_addresses(self) -> address_pb2.AddressList:
        addresses = address_pb2.AddressList()
        for entity in self.addresses.values():
            address = addresses.address.add()
            entity.to_message(address)
        return addresses

    async def rpc_list_address_configs(self) -> address_pb2.AddressConfigList:
        return self.config.staged_data.addresses

    def validate_interface_and_ip(self, msg: address_pb2.AddressConfig):
        if not msg.interface:
            raise RPCInvalidArgument("interface not specified")
        if not msg.ip:
            raise RPCInvalidArgument("ip not specified")
        try:
            ip_interface(msg.ip)
        except ValueError:
            raise RPCInvalidArgument("ip not an IP address")

    async def rpc_add_address(self, msg: address_pb2.AddressConfig) -> None:
        self.validate_interface_and_ip(msg)

        for address in self.config.staged_data.addresses.address:
            if address.interface == msg.interface and ip_interface(
                address.ip
            ) == ip_interface(msg.ip):
                raise RPCInvalidArgument("%s %s" % (msg.interface, msg.ip))
        address = self.config.staged_data.addresses.address.add()
        address.CopyFrom(msg)
        return address

    async def rpc_update_address(self, msg: address_pb2.AddressConfig) -> None:
        self.validate_interface_and_ip(msg)

        for address in self.config.staged_data.addresses.address:
            if address.interface == msg.interface and ip_interface(
                address.ip
            ) == ip_interface(msg.ip):
                address.CopyFrom(msg)

    async def rpc_delete_address(self, msg: address_pb2.AddressConfig) -> None:
        self.validate_interface_and_ip(msg)

        for i, address in enumerate(self.config.staged_data.addresses.address):
            if address.interface == msg.interface and ip_interface(
                address.ip
            ) == ip_interface(msg.ip):
                del self.config.staged_data.addresses.address[i]
