"""
routesia/interface/provider.py - Interface support
"""

import logging
from routesia.config.provider import ConfigProvider
from routesia.exceptions import RPCInvalidParameters, RPCEntityExists
from routesia.injector import Provider
from routesia.interface.entities import INTERFACE_TYPE_ENTITY_MAP, INTERFACE_CONFIG_TYPE_ENTITY_MAP
from routesia.interface import interface_pb2
from routesia.interface import interface_types
from routesia.rpc.provider import RPCProvider
from routesia.rtnetlink.events import InterfaceAddEvent, InterfaceRemoveEvent
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.server import Server


logger = logging.getLogger(__name__)


# Interface config type indexed by type and kind
#
INTERFACE_TYPE_CONFIG_MAP = {
    (interface_types.ARPHRD_ETHER, None): interface_pb2.ETHERNET,
    (interface_types.ARPHRD_ETHER, 'bridge'): interface_pb2.BRIDGE,
    (interface_types.ARPHRD_ETHER, 'vlan'): interface_pb2.VLAN,
    # (interface_types.ARPHRD_INFINIBAND, None): ,
    # (interface_types.ARPHRD_TUNNEL, None): ,
    # (interface_types.ARPHRD_TUNNEL6, None): ,
    (interface_types.ARPHRD_LOOPBACK, None): interface_pb2.LOOPBACK,
    # (interface_types.ARPHRD_SIT, None): ,
    # (interface_types.ARPHRD_IPGRE, None): ,
    # (interface_types.ARPHRD_IEEE80211, None): ,
}


class InterfaceProvider(Provider):
    def __init__(self, server: Server, iproute: IPRouteProvider, config: ConfigProvider, rpc: RPCProvider):
        self.server = server
        self.iproute = iproute
        self.config = config
        self.rpc = rpc
        self.interfaces = {}
        self.running = False

        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

    def on_config_change(self):
        new_interfaces = {}
        for interface in self.config.data.interfaces.interface:
            new_interfaces[interface.name] = interface
        new_interface_names = set(new_interfaces.keys())

        # Remove interfaces that no longer have a config
        for interface in self.interfaces.values():
            if interface.config and interface.name not in new_interface_names:
                interface.on_config_removed()

        # Add/update the rest
        for ifname in new_interface_names:
            if ifname in self.interfaces:
                self.interfaces[ifname].on_config_change(new_interfaces[ifname])
            else:
                entity_class = INTERFACE_CONFIG_TYPE_ENTITY_MAP[interface.type]
                self.interfaces[ifname] = entity_class(self, ifname, config=new_interfaces[ifname])

    def handle_interface_add(self, interface_event):
        map_type = (interface_event.iftype, interface_event.kind)
        ifname = interface_event.ifname

        if ifname in self.interfaces:
            self.interfaces[ifname].update_state(interface_event)
        else:
            if map_type in INTERFACE_TYPE_ENTITY_MAP:
                interface = INTERFACE_TYPE_ENTITY_MAP[map_type](self, ifname)
                interface.update_state(interface_event)
                self.interfaces[ifname] = interface

    def handle_interface_remove(self, interface_event):
        ifname = interface_event.ifname

        if ifname in self.interfaces:
            interface = self.interfaces[ifname]
            interface.on_interface_remove()
            if not interface.config:
                del self.interfaces[ifname]

    def load(self):
        self.config.register_change_handler(self.on_config_change)
        for interface in self.config.data.interfaces.interface:
            entity_class = INTERFACE_CONFIG_TYPE_ENTITY_MAP[interface.type]
            self.interfaces[interface.name] = entity_class(self, interface.name, config=interface)

    def startup(self):
        self.running = True
        self.rpc.register('/interface/list', self.rpc_list_interfaces)
        self.rpc.register('/interface/config/list', self.rpc_list_interface_configs)
        self.rpc.register('/interface/config/add', self.rpc_add_interface_config)
        self.rpc.register('/interface/config/update', self.rpc_update_interface_config)
        self.rpc.register('/interface/config/delete', self.rpc_delete_interface_config)
        for interface in self.interfaces.values():
            interface.startup()

    def shutdown(self):
        self.running = False
        for interface in self.interfaces.values():
            interface.shutdown()

    def get_ifindex(self, ifname):
        if ifname in self.interfaces:
            return self.interfaces[ifname].ifindex
        return None

    def rpc_list_interfaces(self, msg: None) -> interface_pb2.InterfaceList:
        interfaces = interface_pb2.InterfaceList()
        for entity in self.interfaces.values():
            interface = interfaces.interface.add()
            entity.to_message(interface)
        return interfaces

    def rpc_list_interface_configs(self, msg: None) -> interface_pb2.InterfaceConfigList:
        return self.config.staged_data.interfaces

    def rpc_add_interface_config(self, msg: interface_pb2.InterfaceConfig) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for interface in self.config.staged_data.interfaces.interface:
            if interface.name == msg.name:
                raise RPCEntityExists(msg.name)
        interface = self.config.staged_data.interfaces.interface.add()
        interface.CopyFrom(msg)
        return interface

    def rpc_update_interface_config(self, msg: interface_pb2.InterfaceConfig) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for interface in self.config.staged_data.interfaces.interface:
            if interface.name == msg.name:
                interface.CopyFrom(msg)

    def rpc_delete_interface_config(self, msg: interface_pb2.InterfaceConfig) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for i, interface in enumerate(self.config.staged_data.interfaces.interface):
            if interface.name == msg.name:
                del self.config.staged_data.interfaces.interface[i]
