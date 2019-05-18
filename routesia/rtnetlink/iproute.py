"""
routesia_rtnetlink/iproute.py - IPRoute provider
"""

from ipaddress import ip_interface, ip_network
from pyroute2 import IPRoute
import select
import socket
from threading import Thread

from routesia.event import Event
from routesia.injector import Provider
from routesia.server import Server


RT_PROTO = 52


class IgnoreMessage(Exception):
    pass


class RtnetlinkEvent(Event):
    def __init__(self, iproute, message):
        self.message = message
        self.attrs = dict(message['attrs'])


class InterfaceEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)
        self.ifindex = message['index']
        self.iftype = message['ifi_type']
        self.ifname = self.attrs['IFLA_IFNAME']
        self.kind = self.attrs.get('IFLA_KIND', None)


class InterfaceAddEvent(InterfaceEvent):
    pass


class InterfaceRemoveEvent(InterfaceEvent):
    pass


class AddressEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)
        self.ifindex = message['index']
        self.ifname = iproute.interface_map[self.ifindex]
        self.ip = ip_interface(
            '%s/%s' % (self.attrs['IFA_ADDRESS'], message['prefixlen']))


class AddressAddEvent(AddressEvent):
    pass


class AddressRemoveEvent(AddressEvent):
    pass


class RouteEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)
        if message['family'] not in (socket.AF_INET, socket.AF_INET6):
            raise IgnoreMessage
        if 'RTA_DST' in self.attrs:
            self.destination = ip_network(
                '%s/%s' % (self.attrs['RTA_DST'], message['dst_len']))
        else:
            if message['family'] == socket.AF_INET:
                self.destination = ip_network(
                    '0.0.0.0/%s' % message['dst_len'])
            else:
                self.destination = ip_network('::/%s' % message['dst_len'])


class RouteAddEvent(RouteEvent):
    pass


class RouteRemoveEvent(RouteEvent):
    pass


class NeighbourEvent(RtnetlinkEvent):
    def __init__(self, iproute, message):
        super().__init__(iproute, message)


class NeighbourAddEvent(NeighbourEvent):
    pass


class NeighbourRemoveEvent(NeighbourEvent):
    pass


ROUTE_EVENT_MAP = {
    'RTM_NEWLINK': InterfaceAddEvent,
    'RTM_DELLINK': InterfaceRemoveEvent,
    'RTM_NEWADDR': AddressAddEvent,
    'RTM_DELADDR': AddressRemoveEvent,
    'RTM_NEWROUTE': RouteAddEvent,
    'RTM_DELROUTE': RouteRemoveEvent,
    'RTM_NEWNEIGH': NeighbourAddEvent,
    'RTM_DELNEIGH': NeighbourRemoveEvent,
}


class IPRouteProvider(Provider):
    def __init__(self, server: Server):
        self.server = server
        self.iproute = IPRoute()
        self.rt_proto = RT_PROTO
        # ifindex to name map
        self.interface_map = {}
        self.thread = Thread(
            target=self.event_thread,
            name='IProuteEventThread',
            kwargs={
                'server': self.server,
            },
            daemon=True,
        )

    def startup(self):
        self.thread.start()
        # This order is important
        self.get_interfaces()
        self.get_addresses()
        self.get_neighbours()
        self.get_routes()

    def event_thread(self, server: Server):
        with IPRoute() as iproute:
            iproute.bind()

            poller = select.poll()

            poller.register(iproute, select.POLLIN)

            while True:
                events = poller.poll()
                for event in events:
                    if event[0] == iproute.fileno():
                        for message in iproute.get():
                            if message['event'] in ROUTE_EVENT_MAP:
                                try:
                                    event = ROUTE_EVENT_MAP[message['event']](
                                        self, message)
                                except IgnoreMessage:
                                    continue

                                # Update interface map if necessary
                                if message['event'] == 'RTM_NEWLINK':
                                    self.interface_map[event.ifindex] = event.ifname
                                elif message['event'] == 'RTM_DELLINK':
                                    pass
                                    # TODO: Delayed remove in case other events occur
                                    # if event.ifindex in self.interface_map:
                                    #     del self.interface_map[event.ifindex]

                                server.publish_event(event)
                            else:
                                print("Unhandled event %s" % message['event'])

    def get_interfaces(self):
        for message in self.iproute.get_links():
            event = InterfaceAddEvent(self, message)
            self.interface_map[event.ifindex] = event.ifname
            self.server.publish_event(event)

    def get_addresses(self):
        for message in self.iproute.get_addr():
            self.server.publish_event(
                AddressAddEvent(self, message)
            )

    def get_neighbours(self):
        for message in self.iproute.get_neighbours():
            self.server.publish_event(
                NeighbourAddEvent(self, message)
            )

    def get_routes(self):
        for message in self.iproute.get_routes():
            self.server.publish_event(
                RouteAddEvent(self, message)
            )
