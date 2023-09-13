"""
routesia/interface/provider.py - Interface support
"""

import logging
from routesia.config.provider import ConfigProvider
from routesia.rpc import RPCInvalidParameters, RPCEntityExists
from routesia.service import Provider
from routesia.interface.entities import (
    INTERFACE_TYPE_ENTITY_MAP,
    INTERFACE_CONFIG_TYPE_ENTITY_MAP,
)
from routesia.interface import interface_types
from routesia.rpc import RPC
from routesia.rtnetlink.events import InterfaceAddEvent, InterfaceRemoveEvent
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.schema.v1 import interface_pb2
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
        self.interfaces = {}
        self.interface_dependencies = {}
        self.running = False

        self.service.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.service.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)
        self.rpc.register("/interface/list", self.rpc_list_interfaces)
        self.rpc.register("/interface/config/list", self.rpc_list_interface_configs)
        self.rpc.register("/interface/config/add", self.rpc_add_interface_config)
        self.rpc.register("/interface/config/update", self.rpc_update_interface_config)
        self.rpc.register("/interface/config/delete", self.rpc_delete_interface_config)

    def on_config_change(self, config):
        new_interfaces = {}
        for interface in self.config.data.interfaces.interface:
            new_interfaces[interface.name] = interface
        new_interface_names = set(new_interfaces.keys())

        # Remove interfaces that no longer have a config
        for interface in list(self.interfaces.values()):
            if interface.config and interface.name not in new_interface_names:
                interface.on_config_removed()
                for dependent_interface in interface.dependent_interfaces:
                    if (
                        dependent_interface in self.interface_dependencies
                        and interface
                        in self.interface_dependencies[dependent_interface]
                    ):
                        self.interface_dependencies[dependent_interface].remove(
                            interface
                        )

        # Add/update the rest
        for ifname in new_interface_names:
            interface = new_interfaces[ifname]
            if ifname in self.interfaces:
                self.interfaces[ifname].on_config_change(interface)
            else:
                entity_class = INTERFACE_CONFIG_TYPE_ENTITY_MAP[interface.type]
                entity = entity_class(self, ifname, config=interface)
                self.interfaces[ifname] = entity
                entity.startup()

    async def handle_interface_add(self, interface_event):
        map_type = (interface_event.iftype, interface_event.kind)
        ifname = interface_event.ifname

        if ifname in self.interfaces:
            self.interfaces[ifname].update_state(interface_event)
        else:
            if map_type in INTERFACE_TYPE_ENTITY_MAP:
                interface = INTERFACE_TYPE_ENTITY_MAP[map_type](self, ifname)
                interface.update_state(interface_event)
                self.interfaces[ifname] = interface
        if interface_event.ifname in self.interface_dependencies:
            for entity in self.interface_dependencies[interface_event.ifname]:
                entity.on_dependent_interface_add(interface_event)

    async def handle_interface_remove(self, interface_event):
        ifname = interface_event.ifname

        if ifname in self.interface_dependencies:
            for entity in self.interface_dependencies[ifname]:
                entity.on_dependent_interface_add(interface_event)

        if ifname in self.interfaces:
            interface = self.interfaces[ifname]
            interface.on_interface_remove()
            if not interface.config:
                del self.interfaces[ifname]

    def load(self):
        self.config.register_change_handler(self.on_config_change)
        for interface in self.config.data.interfaces.interface:
            entity_class = INTERFACE_CONFIG_TYPE_ENTITY_MAP[interface.type]
            entity = entity_class(self, interface.name, config=interface)
            self.interfaces[interface.name] = entity
            for dependent_interface in entity.dependent_interfaces:
                if dependent_interface not in self.interface_dependencies:
                    self.interface_dependencies[dependent_interface] = []
                self.interface_dependencies[dependent_interface].append(entity)

    def start(self):
        self.running = True
        for interface in self.interfaces.values():
            interface.startup()

    def stop(self):
        self.running = False
        for interface in self.interfaces.values():
            interface.stop()

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

    async def rpc_add_interface_config(self, msg: interface_pb2.InterfaceConfig) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for interface in self.config.staged_data.interfaces.interface:
            if interface.name == msg.name:
                raise RPCEntityExists(msg.name)
        interface = self.config.staged_data.interfaces.interface.add()
        interface.CopyFrom(msg)
        return interface

    async def rpc_update_interface_config(self, msg: interface_pb2.InterfaceConfig) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for interface in self.config.staged_data.interfaces.interface:
            if interface.name == msg.name:
                interface.CopyFrom(msg)

    async def rpc_delete_interface_config(self, msg: interface_pb2.InterfaceConfig) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for i, interface in enumerate(self.config.staged_data.interfaces.interface):
            if interface.name == msg.name:
                del self.config.staged_data.interfaces.interface[i]
