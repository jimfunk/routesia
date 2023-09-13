"""
routesia/rtnetlink/provider.py - IPRoute provider
"""

import logging
from pyroute2 import IPRoute
import select
from threading import Thread

from routesia.service import Provider
from routesia.service import Service
from routesia.rtnetlink.events import (
    InterfaceAddEvent,
    InterfaceRemoveEvent,
    AddressAddEvent,
    AddressRemoveEvent,
    RouteAddEvent,
    RouteRemoveEvent,
    NeighbourAddEvent,
    NeighbourRemoveEvent,
    IgnoreMessage,
)


logger = logging.getLogger("rtnetlink")


RT_PROTO = 52


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


class IPRouteException(Exception):
    pass


class InterfaceDoesNotExist(IPRouteException):
    pass


class IPRouteProvider(Provider):
    def __init__(self, service: Service):
        self.service = service
        self.iproute = IPRoute()
        self.rt_proto = RT_PROTO
        # ifindex to name map
        self.interface_map = {}
        # Name to ifindex map
        self.interface_name_map = {}
        self.thread = Thread(
            target=self.event_thread,
            name='IProuteEventThread',
            kwargs={
                'service': self.service,
            },
            daemon=True,
        )

    def start(self):
        self.thread.start()
        # This order is important
        self.get_interfaces()
        self.get_addresses()
        self.get_neighbours()
        self.get_routes()

    def event_thread(self, service: Service):
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
                                    self.interface_name_map[event.ifname] = event.ifindex
                                elif message['event'] == 'RTM_DELLINK':
                                    pass
                                    # TODO: Delayed remove in case other events occur
                                    # if event.ifindex in self.interface_map:
                                    #     del self.interface_map[event.ifindex]

                                service.publish_event(event)
                            else:
                                logging.warning("Unhandled event %s" % message['event'])

    def get_interfaces(self):
        for message in self.iproute.get_links():
            event = InterfaceAddEvent(self, message)
            self.interface_map[event.ifindex] = event.ifname
            self.interface_name_map[event.ifname] = event.ifindex
            self.service.publish_event(event)

    def get_addresses(self):
        for message in self.iproute.get_addr():
            self.service.publish_event(
                AddressAddEvent(self, message)
            )

    def get_neighbours(self):
        for message in self.iproute.get_neighbours():
            self.service.publish_event(
                NeighbourAddEvent(self, message)
            )

    def get_routes(self):
        for message in self.iproute.get_routes():
            self.service.publish_event(
                RouteAddEvent(self, message)
            )

    def get_interface_name_by_index(self, index):
        try:
            return self.interface_map[index]
        except KeyError:
            raise InterfaceDoesNotExist("Interface does not exist")

    def get_interface_index_by_name(self, name):
        try:
            return self.interface_name_map[name]
        except KeyError:
            raise InterfaceDoesNotExist("Interface does not exist")
