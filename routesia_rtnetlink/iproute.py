"""
routesia_rtnetlink/iproute.py - IPRoute provider
"""

from pyroute2 import IPRoute
from threading import Thread

from routesia.event import Event
from routesia.injector import Provider
from routesia.server import Server


class RtnetlinkEvent(Event):
    def __init__(self, message):
        self.message = message
        self.attrs = dict(message['attrs'])


class InterfaceEvent(RtnetlinkEvent):
    def __init__(self, message):
        super().__init__(message)
        self.ifindex = message['index']
        self.iftype = message['ifi_type']
        self.ifname = self.attrs['IFLA_IFNAME']


class InterfaceAddEvent(InterfaceEvent):
    pass


class InterfaceRemoveEvent(InterfaceEvent):
    pass


ROUTE_EVENT_MAP = {
    'RTM_NEWLINK': InterfaceAddEvent,
    'RTM_DELLINK': InterfaceRemoveEvent,
}


class IPRouteProvider(Provider):
    def __init__(self, server: Server):
        self.server = server
        self.iproute = IPRoute()
        self.thread = Thread(
            target=self.event_thread,
            name='IProuteEventThread',
            kwargs={
                'server': server,
            },
        )
        self.thread.start()

    def event_thread(self, server: Server):
        with IPRoute() as iproute:
            iproute.bind()
            while True:
                for message in iproute.get():
                    if message['event'] in ROUTE_EVENT_MAP:
                        server.publish_event(
                            ROUTE_EVENT_MAP[message['event']](message)
                        )
                    else:
                        print("Unhandled event %s" % message['event'])

    def get_interfaces(self):
        for message in self.iproute.get_links():
            self.server.publish_event(
                InterfaceAddEvent(message)
            )
