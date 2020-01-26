"""
routesia/interface/provider.py - Interface support
"""

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.server import Server
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.rtnetlink.events import InterfaceAddEvent, InterfaceRemoveEvent
from routesia.interface.entities import INTERFACE_TYPE_MAP


class InterfaceProvider(Provider):
    def __init__(self, server: Server, iproute: IPRouteProvider, config: ConfigProvider):
        self.server = server
        self.iproute = iproute
        self.config = config
        self.interfaces = {}

        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

    def handle_config_update(self, old, new):
        pass

    def find_config(self, interface_event):
        section = INTERFACE_TYPE_MAP[(interface_event.iftype, interface_event.kind)].section

        for interface_config in getattr(self.config.data.interface, section):
            # Just do ifname for now. Get clever later
            if interface_config.name == interface_event.ifname:
                return interface_config

    def handle_interface_add(self, interface_event):
        map_type = (interface_event.iftype, interface_event.kind)
        ifname = interface_event.ifname

        if map_type in INTERFACE_TYPE_MAP:
            if ifname not in self.interfaces:
                config = self.find_config(interface_event)
                interface = INTERFACE_TYPE_MAP[map_type](ifname, self.iproute, config=config, event=interface_event)
                self.interfaces[ifname] = interface
            else:
                interface = self.interfaces[ifname]
                interface.update_state(interface_event)

    def handle_interface_remove(self, interface_event):
        map_type = (interface_event.iftype, interface_event.kind)
        ifname = interface_event.ifname

        if map_type in INTERFACE_TYPE_MAP:
            if ifname in self.interfaces:
                self.interfaces[ifname].handle_remove()
                del self.interfaces[ifname]

    def startup(self):
        interface_config = self.config.data.interface
        for field, _ in interface_config.ListFields():
            for interface in getattr(interface_config, field.name):
                # Wipe any existing addresses since we are controlling it
                self.iproute.iproute.flush_addr(label=interface.name)
