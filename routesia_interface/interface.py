"""
routesia_interface/interface.py - Interface support
"""

from routesia.config import Config
from routesia.entity import Entity
from routesia.injector import Provider
from routesia.server import Server
from routesia_rtnetlink.iproute import IPRouteProvider, InterfaceAddEvent, InterfaceRemoveEvent

from routesia_interface import interface_types


class InterfaceEntity(Entity):
    def __init__(self, name, config=None):
        super().__init__(config=config)
        self.name = name
        print("New interface %s. Config: %s" % (self.name, self.config))

    def update_state(self, event):
        self.state['ifindex'] = event.message['index']
        self.state['mtu'] = event.attrs['IFLA_MTU']
        self.state['hwaddr'] = event.attrs['IFLA_ADDRESS']

    def handle_remove(self):
        self.state = {}

    def update_config(self, config):
        self.config = config
        self.apply()

    def apply(self):
        pass


class EthernetInterface(InterfaceEntity):
    section = 'ethernet'


class InfinibandInterface(InterfaceEntity):
    section = 'infiniband'


class IPIPInterface(InterfaceEntity):
    section = 'ipip'


class IPIP6Interface(InterfaceEntity):
    section = 'ipip6'


class LoopbackInterface(InterfaceEntity):
    section = 'loopback'


class SITInterface(InterfaceEntity):
    section = 'sit'


class GREInterface(InterfaceEntity):
    section = 'gre'


class WiFiInterface(InterfaceEntity):
    section = 'wifi'


class InterfaceProvider(Provider):
    def __init__(self, server: Server, config: Config, iproute: IPRouteProvider):
        self.server = server
        self.config = config
        self.iproute = iproute
        self.interface_type_map = {
            interface_types.ARPHRD_ETHER: EthernetInterface,
            interface_types.ARPHRD_INFINIBAND: InfinibandInterface,
            interface_types.ARPHRD_TUNNEL: IPIPInterface,
            interface_types.ARPHRD_TUNNEL6: IPIP6Interface,
            interface_types.ARPHRD_LOOPBACK: LoopbackInterface,
            interface_types.ARPHRD_SIT: SITInterface,
            interface_types.ARPHRD_IPGRE: GREInterface,
            interface_types.ARPHRD_IEEE80211: WiFiInterface,
        }
        # Names used for display and config
        self.interface_typename_map = {
            'ethernet': interface_types.ARPHRD_ETHER,
            'infiniband': interface_types.ARPHRD_INFINIBAND,
            'ipip': interface_types.ARPHRD_TUNNEL,
            'ipip6': interface_types.ARPHRD_TUNNEL6,
            'loopback': interface_types.ARPHRD_LOOPBACK,
            'sit': interface_types.ARPHRD_SIT,
            'gre': interface_types.ARPHRD_IPGRE,
            'wifi': interface_types.ARPHRD_IEEE80211,
        }
        self.interfaces = {}

        self.config.register_section('interface', self)

        self.server.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.server.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

        self.iproute.get_interfaces()

    def find_config(self, interface_event):
        # Just do ifname for now. Get clever later
        return self.config.get(
            'interface',
            self.interface_type_map[interface_event.iftype].section,
            interface_event.ifname
        )

    def handle_interface_add(self, interface_event):
        if interface_event.iftype in self.interface_type_map:
            if interface_event.ifname not in self.interfaces:
                config = self.find_config(interface_event)
                interface = self.interface_type_map[interface_event.iftype](interface_event.ifname, config=config)
            else:
                interface = self.interfaces[interface_event.ifname]
            interface.update_state(interface_event)

    def handle_interface_remove(self, interface_event):
        if interface_event.iftype in self.interface_type_map:
            if interface_event.ifname in self.interfaces:
                self.interfaces[interface_event.ifname].handle_remove()
                if self.interfaces[interface_event.ifname].config is not None:
                    del self.interfaces[interface_event.ifname]
