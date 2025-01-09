"""
routesia/interface/provider.py - Interface support
"""

import logging
from routesia.config.configprovider import ConfigProvider
from routesia.dhcp.dhcpclientevents import (
    DHCPv4LeaseAcquired,
    DHCPv4LeaseLost,
    DHCPv4LeasePreinit,
)
from routesia.rpc import RPCInvalidArgument
from routesia.service import Provider
from routesia.interface.interface import Interface
from routesia.interface import interface_types
from routesia.rpc import RPC
from routesia.netlinkprovider import (
    NetlinkInterfaceAddEvent,
    NetlinkInterfaceDeleteEvent,
)
from routesia.schema.v2 import interface_pb2
from routesia.service import Service


logger = logging.getLogger("interface")


# Interface config type indexed by type and kind
#
INTERFACE_TYPE_CONFIG_MAP = {
    (interface_types.ARPHRD_ETHER, None): interface_pb2.ETHERNET,
    (interface_types.ARPHRD_ETHER, "bridge"): interface_pb2.BRIDGE,
    (interface_types.ARPHRD_ETHER, "vlan"): interface_pb2.VLAN,
    # (interface_types.ARPHRD_INFINIBAND, None): ,
    # (interface_types.ARPHRD_TUNNEL, None): ,
    # (interface_types.ARPHRD_TUNNEL6, None): ,
    (interface_types.ARPHRD_LOOPBACK, None): interface_pb2.LOOPBACK,
    (interface_types.ARPHRD_SIT, None): interface_pb2.SIT,
    # (interface_types.ARPHRD_IPGRE, None): ,
    # (interface_types.ARPHRD_IEEE80211, None): ,
}


class InterfaceProvider(Provider):
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

        # Interface add events from netlink
        #
        self.interface_events: dict[str, NetlinkInterfaceAddEvent] = {}

        # Interface entities from configuration
        #
        self.interfaces: dict[str, Interface] = {}

        self.running = False

        self.config.register_change_handler(self.handle_config_change)

        self.service.subscribe_event(NetlinkInterfaceAddEvent, self.handle_interface_add)
        self.service.subscribe_event(NetlinkInterfaceDeleteEvent, self.handle_interface_delete)
        self.service.subscribe_event(DHCPv4LeasePreinit, self.handle_dhcp_lease_preinit)
        self.service.subscribe_event(
            DHCPv4LeaseAcquired, self.handle_dhcp_lease_acquired
        )
        self.service.subscribe_event(DHCPv4LeaseLost, self.handle_dhcp_lease_lost)

        self.rpc.register("interface/list", self.rpc_list_interfaces)
        self.rpc.register("interface/config/list", self.rpc_list_interface_configs)
        self.rpc.register("interface/config/add", self.rpc_add_interface_config)
        self.rpc.register("interface/config/update", self.rpc_update_interface_config)
        self.rpc.register("interface/config/delete", self.rpc_delete_interface_config)

    async def start(self):
        self.running = True
        for config in self.config.data.interfaces.interface:
            self.interfaces[config.name] = Interface(config)
            await self.interfaces[config.name].start(self.interface_events)

    async def stop(self):
        self.running = False
        for interface in self.interfaces.values():
            await interface.stop()
        self.interfaces = {}

    async def handle_config_change(self, config):
        new_interface_names = set()
        for interface_config in self.config.data.interfaces.interface:
            new_interface_names.add(interface_config.name)

        # Remove interfaces that no longer have a config
        for name in self.interfaces:
            if name not in new_interface_names:
                await self.interfaces[name].stop()
                del self.interfaces[name]

        # TODO: Detect itype change

        # Add/update the rest
        for interface_config in self.config.data.interfaces.interface:
            if interface_config.name in self.interfaces:
                await self.interfaces[name].handle_config_change(interface_config, self.interface_events)
            else:
                self.interfaces[config.name] = Interface(
                    config, event=self.interface_events.get(config.name, None)
                )
                await self.interfaces[config.name].start(self.interface_events)

    async def handle_interface_add(self, interface_event: NetlinkInterfaceAddEvent):
        ifname = interface_event.ifname
        self.interface_events[ifname] = interface_event

        # We pass all interface events to all interfaces since some of them, such as
        # vlans, depend on other interfaces to exist
        for interface in self.interfaces.values():
            await interface.handle_interface_add(interface_event)

    async def handle_interface_delete(self, interface_event: NetlinkInterfaceDeleteEvent):
        ifname = interface_event.ifname

        if ifname in self.interface_events:
            del self.interface_events[ifname]

        for interface in self.interfaces.values():
            await interface.handle_interface_delete(interface_event)

    async def handle_address_add(self, address: AddressAddEvent):
        pass

    async def handle_address_remove(self, address: AddressRemoveEvent):
        pass

    async def handle_dhcp_lease_preinit(self, event: DHCPv4LeasePreinit):
        if event.interface in self.interfaces:
            await self.interfaces[event.interface].handle_dhcp_lease_preinit(event)

    async def handle_dhcp_lease_acquired(self, event: DHCPv4LeaseAcquired):
        pass

    async def handle_dhcp_lease_lost(self, event: DHCPv4LeaseLost):
        pass

    def get_ifindex(self, ifname):
        if ifname in self.interfaces:
            return self.interfaces[ifname].ifindex
        return None

    def set_dynamic_config(self, ifname, config):
        "Set dynamic interface config"
        if ifname in self.interfaces:
            self.interfaces[ifname].set_dynamic_config(config)

    async def rpc_list_interfaces(self) -> interface_pb2.InterfaceList:
        interfaces = interface_pb2.InterfaceList()
        for entity in self.interfaces.values():
            interface = interfaces.interface.add()
            entity.to_message(interface)
        return interfaces

    async def rpc_list_interface_configs(self) -> interface_pb2.InterfaceConfigList:
        return self.config.staged_data.interfaces

    async def rpc_add_interface_config(
        self, msg: interface_pb2.InterfaceConfig
    ) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        for interface in self.config.staged_data.interfaces.interface:
            if interface.name == msg.name:
                raise RPCInvalidArgument(msg.name)
        interface = self.config.staged_data.interfaces.interface.add()
        interface.CopyFrom(msg)
        return interface

    async def rpc_update_interface_config(
        self, msg: interface_pb2.InterfaceConfig
    ) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        for interface in self.config.staged_data.interfaces.interface:
            if interface.name == msg.name:
                interface.CopyFrom(msg)

    async def rpc_delete_interface_config(
        self, msg: interface_pb2.InterfaceConfig
    ) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        for i, interface in enumerate(self.config.staged_data.interfaces.interface):
            if interface.name == msg.name:
                del self.config.staged_data.interfaces.interface[i]
