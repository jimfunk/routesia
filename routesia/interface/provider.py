"""
routesia/interface/provider.py - Interface support
"""

import logging
from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.interface.entities import INTERFACE_TYPE_ENTITY_MAP
from routesia.interface.interface_pb2 import InterfaceConfig, InterfaceList
from routesia.interface import interface_types
from routesia.rpc.provider import RPCProvider
from routesia.rtnetlink.events import InterfaceAddEvent, InterfaceRemoveEvent
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.server import Server


logger = logging.getLogger(__name__)


# Interface config type indexed by type and kind
#
INTERFACE_TYPE_CONFIG_MAP = {
    (interface_types.ARPHRD_ETHER, None): InterfaceConfig.INTERFACE_ETHERNET,
    (interface_types.ARPHRD_ETHER, 'bridge'): InterfaceConfig.INTERFACE_BRIDGE,
    (interface_types.ARPHRD_ETHER, 'vlan'): InterfaceConfig.INTERFACE_VLAN,
    # (interface_types.ARPHRD_INFINIBAND, None): ,
    # (interface_types.ARPHRD_TUNNEL, None): ,
    # (interface_types.ARPHRD_TUNNEL6, None): ,
    (interface_types.ARPHRD_LOOPBACK, None): InterfaceConfig.INTERFACE_LOOPBACK,
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

        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

    def handle_config_update(self, old, new):
        pass

    def find_config(self, interface_event):
        # section = INTERFACE_TYPE_ENTITY_MAP[(interface_event.iftype, interface_event.kind)].section

        for interface_config in self.config.data.interface.interface:
            # Just do ifname for now. Get clever later
            if interface_config.name == interface_event.ifname:
                if INTERFACE_TYPE_CONFIG_MAP[(interface_event.iftype, interface_event.kind)] == interface_config.type:
                    return interface_config
                else:
                    logger.warning(
                        "Could not apply interface config for %s because the config type does not match the existing interface type." %
                        interface_event.ifname
                    )

    def handle_interface_add(self, interface_event):
        map_type = (interface_event.iftype, interface_event.kind)
        ifname = interface_event.ifname

        if map_type in INTERFACE_TYPE_ENTITY_MAP:
            if ifname not in self.interfaces:
                config = self.find_config(interface_event)
                interface = INTERFACE_TYPE_ENTITY_MAP[map_type](ifname, self.iproute, config=config, event=interface_event)
                self.interfaces[ifname] = interface
            else:
                interface = self.interfaces[ifname]
                interface.update_state(interface_event)

    def handle_interface_remove(self, interface_event):
        map_type = (interface_event.iftype, interface_event.kind)
        ifname = interface_event.ifname

        if map_type in INTERFACE_TYPE_ENTITY_MAP:
            if ifname in self.interfaces:
                self.interfaces[ifname].handle_remove()
                del self.interfaces[ifname]

    def rpc_list_interfaces(self, msg):
        interfaces = InterfaceList()
        for entity in self.interfaces.values():
            interface = interfaces.interface.add()
            interface.name = entity.name
            if entity.config:
                interface.config.CopyFrom(entity.config)
        return interfaces

    def startup(self):
        self.rpc.register('/interface/list', self.rpc_list_interfaces)
        interface_module_config = self.config.data.interface
        for interface_config in interface_module_config.interface:
            # Wipe any existing addresses since we are controlling it
            self.iproute.iproute.flush_addr(label=interface_config.name)
