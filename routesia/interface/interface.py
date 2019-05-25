"""
routesia/interface/interface.py - Interface support
"""

from routesia.config import ConfigProvider
from routesia.entity import Entity
from routesia.injector import Provider
from routesia.server import Server
from routesia.rtnetlink.iproute import IPRouteProvider, InterfaceAddEvent, InterfaceRemoveEvent
from routesia.interface import interface_flags
from routesia.interface import interface_types
from routesia.interface.interface_pb2 import InterfaceLink


class InterfaceEntity(Entity):
    def __init__(self, name, iproute, config=None, event=None):
        super().__init__(config=config)
        self.name = name
        self.iproute = iproute
        self.ifindex = None
        self.carrier = False
        self.state = InterfaceLink()
        if event:
            self.update_state(event, apply=False)
        print("New %s interface %s. Config: %s" % (self.section, self.name, self.config))
        self.apply()

    def update_state(self, event, apply=True):
        link = event.message
        self.ifindex = link['index']
        self.carrier = bool(event.attrs['IFLA_CARRIER'])

        self.state.up = link['flags'] & interface_flags.IFF_UP
        self.state.noarp = link['flags'] & interface_flags.IFF_NOARP
        self.state.txqueuelen = event.attrs['IFLA_TXQLEN']
        self.state.mtu = event.attrs['IFLA_MTU']
        self.state.address = event.attrs['IFLA_ADDRESS']
        self.state.broadcast = event.attrs['IFLA_BROADCAST']

        if 'IFLA_AF_SPEC' in event.attrs:
            af_attrs = dict(event.attrs['IFLA_AF_SPEC']['attrs'])
            if 'AF_INET6' in af_attrs:
                af_inet6_attrs = dict(af_attrs['AF_INET6']['attrs'])
                self.state.addrgenmode = af_inet6_attrs['IFLA_INET6_ADDR_GEN_MODE']
                self.state.token = af_inet6_attrs['IFLA_INET6_TOKEN']

        if apply:
            self.apply()

    def handle_remove(self):
        self.state.Clear()
        self.apply()

    def update_config(self, config):
        self.config = config
        self.apply()

    def link(self, *args, **kwargs):
        if 'add' not in args:
            kwargs['index'] = self.ifindex
        return self.iproute.iproute.link(*args, **kwargs)

    def apply(self):
        if self.config is not None:
            # Perhaps it would be better to do the reverse of update_state
            # here if they don't match. Have to account for elements left
            # unset though
            if self.state.up is not self.config.link.up:
                self.link('set', state='up' if self.config.link.up else 'down')


class EthernetInterface(InterfaceEntity):
    section = 'ethernet'


class BridgeInterface(InterfaceEntity):
    section = 'bridge'


class VLANInterface(InterfaceEntity):
    section = 'vlan'


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


# Interface class map indexed by type and kind
#
INTERFACE_TYPE_MAP = {
    (interface_types.ARPHRD_ETHER, None): EthernetInterface,
    (interface_types.ARPHRD_ETHER, 'bridge'): BridgeInterface,
    (interface_types.ARPHRD_ETHER, 'vlan'): VLANInterface,
    # (interface_types.ARPHRD_INFINIBAND, None): InfinibandInterface,
    # (interface_types.ARPHRD_TUNNEL, None): IPIPInterface,
    # (interface_types.ARPHRD_TUNNEL6, None): IPIP6Interface,
    (interface_types.ARPHRD_LOOPBACK, None): LoopbackInterface,
    # (interface_types.ARPHRD_SIT, None): SITInterface,
    # (interface_types.ARPHRD_IPGRE, None): GREInterface,
    # (interface_types.ARPHRD_IEEE80211, None): WiFiInterface,
}


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
