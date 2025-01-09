"""
Netlink provider
"""

import asyncio
import contextlib
from dataclasses import dataclass
import logging
from pyroute2 import IPRoute
import selectors
from threading import Thread

from routesia.service import Provider
from routesia.service import Event, Service


logger = logging.getLogger("netlink")


RT_PROTO = 52


class NetlinkException(Exception):
    pass


class InterfaceDoesNotExist(NetlinkException):
    pass


@dataclass(slots=True)
class NetlinkInterfaceAddEvent(Event):
    name: str
    type: int
    index: int
    flags: int
    state: str
    attrs: dict


@dataclass(slots=True)
class NetlinkInterfaceDeleteEvent(Event):
    name: str
    type: int
    index: int
    attrs: dict


class NetlinkProvider(Provider):
    """
    Handles netlink events, tracking the state of the objects.
    """

    def __init__(self, service: Service):
        self.service = service
        self.iproute = IPRoute()

        # TODO: kill. We can set this on addresses and routes directly when we mobe those methods here
        self.rt_proto = RT_PROTO

        # This is used to serialize access to self.iproute
        self.lock = asyncio.Lock()

        # Interface add events indexed by name
        self.interfaces: dict[str, NetlinkInterfaceAddEvent] = {}

        # Interface add events indexed by index
        self.interfaces_by_index: dict[int, NetlinkInterfaceAddEvent] = {}


        # Event thread
        self.thread: Thread | None = None

    async def start(self):
        """
        Start provider.
        """
        self.thread = Thread(
            target=self._event_thread,
            name="NetlinkProviderEventThread",
            daemon=True,
        )
        self.thread.start()

        # This order is important
        await self._enumerate_interfaces()
        # self.get_addresses()
        # self.get_neighbours()
        # self.get_routes()

    def get_interface(
        self, name: str | None = None, index: int | None = None
    ) -> NetlinkInterfaceAddEvent | None:
        """
        Get interface by name or index.

        If the interface does not exist, returns ``None``.
        """
        if name is not None:
            return self.interfaces.get(name)
        try:
            return self.interfaces_by_index[index]
        except KeyError:
            raise InterfaceDoesNotExist(name)

    async def link_set(self, name, **params):
        if name not in self.interfaces:
            raise InterfaceDoesNotExist(name)
        async with self.lock:
            self.iproute.link("set", index=self.interfaces[name].index, **params)

    async def link_add(self, name: str, kind: str, **params):
        async with self.lock:
            self.iproute.link("add", ifname=name, kind=kind, **params)

    async def link_delete(self, name: str):
        if name not in self.interfaces:
            raise InterfaceDoesNotExist(name)
        async with self.lock:
            self.iproute.link("del", index=self.interfaces[name].index)

    def _event_thread(self):
        with IPRoute() as iproute:
            iproute.bind()

            selector = selectors.DefaultSelector()
            selector.register(iproute, selectors.EVENT_READ)

            while True:
                events = selector.select()
                for _ in events:
                    for message in iproute.get():
                        handler_name = f"_handle_{message['event']}"
                        handler = getattr(self, handler_name, None)
                        if handler:
                            try:
                                handler(message)
                            except Exception:
                                logger.exception(f"Caught exception in {handler_name}")

    def _parse_attrs(self, attrlist: list[tuple]) -> dict:
        attrs = {}
        for attr, value in attrlist:
            if attr == "UNKNOWN":
                continue
            attrs[attr] = value
        return attrs

    async def _enumerate_interfaces(self):
        async with self.lock:
            for message in self.iproute.get_links():
                self._handle_RTM_NEWLINK(message)

    def _handle_RTM_NEWLINK(self, message: dict):
        attrs = self._parse_attrs(message["attrs"])
        event = NetlinkInterfaceAddEvent(
            name=attrs["IFLA_IFNAME"],
            type=message["ifi_type"],
            index=message["index"],
            flags=message["flags"],
            state=message["state"],
            attrs=attrs,
        )
        self.interfaces[event.name] = event
        self.interfaces_by_index[event.index] = event
        self.service.publish_event(event)

    def _handle_RTM_DELLINK(self, message: dict):
        attrs = self._parse_attrs(message["attrs"])
        event = NetlinkInterfaceDeleteEvent(
            name=attrs["IFLA_IFNAME"],
            index=message["index"],
            type=message["ifi_type"],
            attrs=attrs,
        )
        if event.name in self.interfaces:
            del self.interfaces[event.name]
        if event.index in self.interfaces_by_index:
            del self.interfaces_by_index[event.index]
        self.service.publish_event(event)
