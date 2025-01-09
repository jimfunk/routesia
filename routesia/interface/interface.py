"""
Interface configuration
"""

import asyncio
from dataclasses import dataclass
from enum import IntEnum
import errno
import ipaddress
import logging
from typing import Type
from pyroute2.netlink.rtnl import ifinfmsg

from routesia.config.configprovider import InvalidConfig
from routesia.dhcp.dhcpclientevents import DHCPv4LeasePreinit
from routesia.interface.eui import EUI
from routesia.netlinkprovider import (
    NetlinkInterfaceAddEvent,
    NetlinkInterfaceDeleteEvent,
    NetlinkProvider,
)
from routesia.schema.v2 import interface_pb2
from routesia.service import Service


logger = logging.getLogger("interface")


class InterfaceError(Exception):
    pass


class InterfaceState(IntEnum):
    STOPPED = interface_pb2.InterfaceStatus.InterfaceState.STOPPED
    WAITING = interface_pb2.InterfaceStatus.InterfaceState.WAITING
    CREATING = interface_pb2.InterfaceStatus.InterfaceState.CREATING
    CONFIGURING = interface_pb2.InterfaceStatus.InterfaceState.CONFIGURING
    CONFIGURED = interface_pb2.InterfaceStatus.InterfaceState.CONFIGURED
    DECONFIGURING = interface_pb2.InterfaceStatus.InterfaceState.DECONFIGURING
    DESTROYING = interface_pb2.InterfaceStatus.InterfaceState.DESTROYING


@dataclass
class InterfaceStateChange:
    name: str
    state: InterfaceState


class Interface:
    def __init__(self, config: interface_pb2.InterfaceConfig, service: Service, netlink: NetlinkProvider):
        self.config = config
        self.service = service
        self.netlink = netlink

        self.link: "Link" | None = None
        self.lock = asyncio.Lock()

        # Track interface event
        self.event: NetlinkInterfaceAddEvent | None = None

        # Keep the first event to save initial values
        self.initial_event: NetlinkInterfaceAddEvent | None = None

        # Track dependent interfaces when appropriate
        self.dependent_interfaces: dict[str, NetlinkInterfaceAddEvent | None] = {}

        self.state = InterfaceState.STOPPED

    def __str__(self):
        return f"Interface {self.config.name}"

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state: InterfaceState):
        self._state = state
        logger.debug(f"{self} entered state {state.name}")
        self.service.publish_event(InterfaceStateChange(self.config.name, state))

    def get_link_class(self) -> Type["Link"]:
        if self.config.type == interface_pb2.ETHERNET:
            return EthernetLink
        if self.config.type == interface_pb2.BRIDGE:
            return BridgeLink
        raise InvalidConfig(f"Unhandled interface type {self.config.type}")

    def subscribe_interface(self):
        """
        Subscribe to updates for the configured interface.

        If the interface already exists the event will be set.
        """
        self.service.subscribe_event(NetlinkInterfaceAddEvent, self.handle_interface_add, name=self.config.name)
        self.service.subscribe_event(NetlinkInterfaceDeleteEvent, self.handle_interface_delete, name=self.config.name)
        self.event = self.netlink.get_interface(self.config.name)
        if self.initial_event is None:
            self.initial_event = self.event

    def get_dependent_interface_names(self) -> list[str]:
        """
        Get a list of interfaces that need to exist before this one can be set up.
        """
        interfaces = []
        if self.config.link.master:
            interfaces.append(self.config.link.master)
        if self.link:
            interfaces += self.link.get_dependent_interface_names()
        return interfaces

    def unsubscribe_interface(self):
        """
        Unsubscribe from updates for the configured interface.
        """
        self.service.unsubscribe_event(NetlinkInterfaceAddEvent, self.handle_interface_add, name=self.config.name)
        self.service.unsubscribe_event(NetlinkInterfaceDeleteEvent, self.handle_interface_delete, name=self.config.name)
        self.event = None

    def subscribe_dependent_interfaces(self):
        """
        Subscribe to updates for the configured master interface if set.

        If the interface already exists the event will be set.
        """
        for name in self.get_dependent_interface_names():
            self.service.subscribe_event(NetlinkInterfaceAddEvent, self.handle_dependent_interface_add, name=name)
            self.service.subscribe_event(NetlinkInterfaceDeleteEvent, self.handle_dependent_interface_delete, name=name)
            self.master_event = self.netlink.get_interface(name)

    def unsubscribe_dependent_interfaces(self):
        """
        Unsubscribe from updates for the configured master interface if set.
        """
        for name in self.dependent_interfaces.keys():
            self.service.unsubscribe_event(NetlinkInterfaceAddEvent, self.handle_dependent_interface_add, name=name)
            self.service.unsubscribe_event(NetlinkInterfaceDeleteEvent, self.handle_dependent_interface_delete, name=name)
        self.dependent_interfaces = {}

    async def start(self):
        """
        Start interface.
        """
        if self.state != InterfaceState.STOPPED:
            return

        if self.config.disable:
            return

        async with self.lock:
            self.link = self.get_link_class()(self)
            self.state = InterfaceState.WAITING
            self.subscribe_interface()

            if self.link.virtual:
                if not all(self.dependent_interfaces.values()):
                    # Can't start yet. Wait for dependent interfaces
                    return

                self.state = InterfaceState.CREATING
                await self.link.create()
                return
            elif not self.event or not all(self.dependent_interfaces.values()):
                return

            self.state = InterfaceState.CONFIGURING
            await self.configure()
            self.state = InterfaceState.CONFIGURED

    async def stop(self):
        if self.state == InterfaceState.STOPPED:
            return

        async with self.lock:
            if self.state == InterfaceState.CONFIGURED:
                self.state = InterfaceState.DECONFIGURING
                await self.deconfigure()

            if self.link.virtual and self.event:
                self.state = InterfaceState.DESTROYING
                await self.link.delete()
                return

            self.unsubscribe_interface()
            self.unsubscribe_dependent_interfaces()
            self.link = None
            self.state = InterfaceState.STOPPED

    async def configure(self):
        await self.set_params(self.get_link_start_params())

    async def deconfigure(self):
        await self.set_params(self.get_link_stop_params())

    async def handle_config_change(self, config: interface_pb2.InterfaceConfig):
        if self.state == InterfaceState.STOPPED:
            self.config = config
            return

        old_config = self.config
        await self.handle_config_change_pre(old_config, config)
        self.config = config
        await self.handle_config_change_post(old_config, config)

    async def handle_config_change_pre(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig):
        if new_config.disable or self.link.needs_restart(old_config, new_config):
            await self.stop()
            return

        async with self.lock:
            self.unsubscribe_dependent_interfaces()

    async def handle_config_change_post(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig):
        if new_config.disable:
            return

        if self.state == InterfaceState.STOPPED:
            await self.start()
            return

        async with self.lock:
            self.subscribe_dependent_interfaces()

            link_params = self.get_link_change_params(old_config, new_config)
            if link_params:
                await self.set_params(link_params)

    def get_link_start_params(self) -> dict:
        """
        Return start params to pass to Pyroute2 link set according to the config.
        """
        link = self.config.link

        flags = ifinfmsg.IFF_UP
        change = ifinfmsg.IFF_UP | ifinfmsg.IFF_NOARP

        if link.noarp:
            flags |= ifinfmsg.IFF_NOARP

        params = {
            "flags": flags,
            "change": change,
        }

        af_spec = []
        af_inet6 = []

        if link.txqueuelen:
            params["txqlen"] = link.txqueuelen
        if link.mtu:
            params["mtu"] = link.mtu
        if link.address:
            params["address"] = link.address
        if link.broadcast:
            params["broadcast"] = link.broadcast
        if link.master:
            params["master"] = self.master_event.index
        if link.addrgenmode:
            af_inet6.append(("IFLA_INET6_ADDR_GEN_MODE", link.addrgenmode))
        if link.token:
            af_inet6.append(("IFLA_INET6_TOKEN", link.token))

        if af_inet6:
            af_spec.append(("AF_INET6", {"attrs": af_inet6}))
        if af_spec:
            params["IFLA_AF_SPEC"] = {"attrs": af_spec}

        return params

    def get_link_stop_params(self) -> dict:
        """
        Return stop params to pass to Pyroute2 link set.
        """
        params = {}

        if self.initial_event:
            params["flags"] = self.initial_event.flags
            params["txqlen"] = self.initial_event.attrs["IFLA_TXQLEN"]
            params["mtu"] = self.initial_event.attrs["IFLA_MTU"]
            params["address"] = self.initial_event.attrs["IFLA_ADDRESS"]
            params["broadcast"] = self.initial_event.attrs["IFLA_BROADCAST"]
            if "IFLA_AF_SPEC" in self.initial_event.attrs:
                af_spec_attrs = []
                af_spec = dict(self.initial_event.attrs["IFLA_AF_SPEC"]["attrs"])
                if "AF_INET6" in af_spec:
                    af_inet6_attrs = []
                    af_inet6 = dict(af_spec["AF_INET6"]["attrs"])
                    if "IFLA_INET6_ADDR_GEN_MODE" in af_inet6:
                        af_inet6_attrs.append(("IFLA_INET6_ADDR_GEN_MODE", af_inet6["IFLA_INET6_ADDR_GEN_MODE"]))
                    if "IFLA_INET6_TOKEN" in af_inet6:
                        af_inet6_attrs.append(("IFLA_INET6_TOKEN", af_inet6["IFLA_INET6_TOKEN"]))
                    if af_inet6_attrs:
                        af_spec_attrs.append(("AF_INET6", {"attrs": af_inet6_attrs}))
                if af_spec_attrs:
                    params["IFLA_AF_SPEC"] = {"attrs": af_spec_attrs}

        print(params)

        return params

    def get_link_change_params(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig) -> dict:
        """
        Return link params that should be changed.
        """
        params = {}
        af_spec = []
        af_inet6 = []

        old_link = old_config.link
        new_link = new_config.link

        if new_link.noarp != old_link.noarp:
            if new_link.noarp:
                params["flags"] = ifinfmsg.IFF_NOARP
            else:
                params["flags"] = 0
            params["change"] = ifinfmsg.IFF_NOARP

        if new_link.txqueuelen != old_link.txqueuelen:
            if new_link.txqueuelen:
                params["txqlen"] = new_link.txqueuelen
            else:
                params["txqlen"] = self.initial_event.attrs["IFLA_TXQLEN"]
        if new_link.mtu != old_link.mtu:
            if new_link.mtu:
                params["mtu"] = new_link.mtu
            else:
                params["mtu"] = self.initial_event.attrs["IFLA_MTU"]
        if new_link.address != old_link.address:
            if new_link.address:
                params["address"] = new_link.address
            else:
                params["address"] = self.initial_event.attrs["IFLA_ADDRESS"]
        if new_link.broadcast != old_link.broadcast:
            if new_link.broadcast:
                params["broadcast"] = new_link.broadcast
            else:
                params["broadcast"] = self.initial_event.attrs["IFLA_BROADCAST"]
        if new_link.master != old_link.master:
            params["master"] = self.master_event.index if new_link.master else 0
        if new_link.addrgenmode != old_link.addrgenmode:
            af_inet6.append(("IFLA_INET6_ADDR_GEN_MODE", new_link.addrgenmode))
        if new_link.token != old_link.token:
            af_inet6.append(("IFLA_INET6_TOKEN", new_link.token))

        if af_inet6:
            af_spec.append(("AF_INET6", {"attrs": af_inet6}))
        if af_spec:
            params["IFLA_AF_SPEC"] = {"attrs": af_spec}

        return params

    async def set_params(self, params):
        logger.info(f"Setting link params for {self.config.name}: {params}")
        await self.netlink.link_set(self.config.name, **params)

    async def handle_interface_add(self, event: NetlinkInterfaceAddEvent):
        async with self.lock:
            if self.initial_event is None:
                self.initial_event = event
            self.event = event
            if self.state in (InterfaceState.WAITING, InterfaceState.CREATING):
                if all(self.dependent_interfaces.values()):
                    self.state = InterfaceState.CONFIGURING
                    await self.configure()
                    self.state = InterfaceState.CONFIGURED

    async def handle_interface_delete(self, event: NetlinkInterfaceDeleteEvent):
        async with self.lock:
            self.event = None
            if self.state == InterfaceState.CONFIGURED:
                await self.deconfigure()
                self.state = InterfaceState.STOPPED
            elif self.state == InterfaceState.DESTROYING:
                self.unsubscribe_interface()
                self.unsubscribe_dependent_interfaces()
                self.link = None
                self.state = InterfaceState.STOPPED

    async def handle_dependent_interface_add(self, event: NetlinkInterfaceAddEvent):
        async with self.lock:
            self.dependent_interfaces[event.name] = event
            if self.state == InterfaceState.WAITING:
                if all(self.dependent_interfaces.values()) and self.event:
                    self.state = InterfaceState.CONFIGURING
                    await self.configure()
                    self.state = InterfaceState.CONFIGURED

    async def handle_dependent_interface_delete(self, event: NetlinkInterfaceDeleteEvent):
        async with self.lock:
            self.dependent_interfaces[event.name] = None
            if self.state == InterfaceState.CONFIGURED:
                await self.deconfigure()
                if self.link.virtual:
                    self.state = InterfaceState.DESTROYING
                    await self.link.delete()
                else:
                    self.state = InterfaceState.WAITING

class Link:
    virtual: bool = False

    def __init__(self, interface: Interface):
        self.interface = interface

    def get_dependent_interface_names(self) -> list[str]:
        return []

    def needs_restart(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig) -> bool:
        return False

    def get_link_change_params(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig) -> dict:
        return {}

    async def create(self):
        pass

    async def delete(self):
        pass


class EthernetLink(Link):
    pass


class BridgeLink(Link):
    virtual = True

    def get_link_create_params(self):
        params = {}
        if self.interface.config.bridge.ageing_time:
            params["br_ageing_time"] = self.interface.config.bridge.ageing_time
        if self.interface.config.bridge.forward_delay:
            params["br_forward_delay"] = self.interface.config.bridge.forward_delay
        if self.interface.config.bridge.hello_time:
            params["br_hello_time"] = self.interface.config.bridge.hello_time
        if self.interface.config.bridge.max_age:
            params["br_max_age"] = self.interface.config.bridge.max_age
        params["br_stp_state"] = self.interface.config.bridge.stp
        if self.interface.config.bridge.priority:
            params["br_priority"] = self.interface.config.bridge.priority
        params["br_vlan_filtering"] = self.interface.config.bridge.vlan_filtering
        if self.interface.config.bridge.default_pvid:
            params["br_vlan_default_pvid"] = self.interface.config.bridge.default_pvid

        return params

    def get_link_change_params(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig) -> dict:
        params = {}

        old_bridge = old_config.bridge
        new_bridge = new_config.bridge

        if new_bridge.ageing_time != old_bridge.ageing_time:
            params["br_ageing_time"] = new_bridge.ageing_time
        if new_bridge.forward_delay != old_bridge.forward_delay:
            params["br_forward_delay"] = new_bridge.forward_delay
        if new_bridge.hello_time != old_bridge.hello_time:
            params["br_hello_time"] = new_bridge.hello_time
        if new_bridge.max_age != old_bridge.max_age:
            params["br_max_age"] = new_bridge.max_age
        if new_bridge.stp != old_bridge.stp:
            params["br_stp_state"] = new_bridge.stp
        if new_bridge.priority != old_bridge.priority:
            params["br_priority"] = new_bridge.priority
        if new_bridge.vlan_filtering != old_bridge.vlan_filtering:
            params["br_vlan_filtering"] = new_bridge.vlan_filtering
        if new_bridge.default_pvid != old_bridge.default_pvid:
            params["br_vlan_default_pvid"] = new_bridge.default_pvid

        return params

    async def create(self):
        await self.interface.netlink.link_add(
            self.interface.config.name,
            "bridge",
            **self.get_link_create_params(),
        )

    async def delete(self):
        await self.interface.netlink.link_delete(self.interface.config.name)


class VLANLink(Link):
    virtual = True

    def get_dependent_interface_names(self) -> list[str]:
        return [self.interface.config.vlan.trunk]

    def get_link_create_params(self):
        params = {
            "link": self.interface.dependent_interfaces[self.interface.config.vlan.trunk].index,
            "vlan_id": self.interface.config.vlan.id,
        }

        flags = []

        if self.interface.config.vlan.gvrp:
            flags.append("gvrp")
        if self.interface.config.vlan.mvrp:
            flags.append("mvrp")

        if flags:
            params["vlan_flags"] = flags

        return params

    def needs_restart(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig) -> bool:
        if old_config.vlan.trunk != new_config.vlan.trunk:
            return True
        return False

    def get_link_change_params(self, old_config: interface_pb2.InterfaceConfig, new_config: interface_pb2.InterfaceConfig) -> dict:
        params = {}

        old_vlan = old_config.vlan
        new_vlan = new_config.vlan

        if new_vlan.id != old_vlan.id:
            params["vlan_id"] = new_vlan.id

        if new_vlan.gvrp != old_vlan.gvrp or new_vlan.mvrp != old_vlan.mvrp:
            flags = []

            if self.interface.config.vlan.gvrp:
                flags.append("gvrp")
            if self.interface.config.vlan.mvrp:
                flags.append("mvrp")

            params["vlan_flags"] = flags

        return params

    async def create(self):
        await self.interface.netlink.link_add(
            self.interface.config.name,
            "vlan",
            **self.get_link_create_params(),
        )

    async def delete(self):
        await self.interface.netlink.link_delete(self.interface.config.name)


# class VXLANInterface(BaseInterface):
#     def __init__(self, config):
#         super().__init__(config)
#         self.link: NetlinkInterfaceAddEvent | None = None
#         self.vxlan: NetlinkInterfaceAddEvent | None = None

#     async def start(self, interfaces: dict[str, NetlinkInterfaceAddEvent]):
#         if self.config.link and self.config.link in interfaces:
#             self.link = interfaces[self.config.link]

#         if self.config.name in interfaces:
#             interface = interfaces[self.config.name]
#             if interface.kind == "vxlan":
#                 linkinfo = dict(interface.attrs["IFLA_LINKINFO"]["attrs"])
#                 infodata = dict(linkinfo["IFLA_INFO_DATA"]["attrs"])

#                 if (
#                     infodata["IFLA_VXLAN_ID"] == self.config.vxlan.id
#                     and infodata["IFLA_VXLAN_PORT"] == self.config.vxlan.port
#                     and infodata["IFLA_VXLAN_PORT"] == self.trunk.ifindex
#                 ):
#                     self.interface = interface
#                     self.netlink.link(
#                         "set", ifname=self.config.name, vlan_flags=self.build_flags()
#                     )
#                 else:
#                     logger.warning(
#                         f"Interface {self.config.name} is defined as a VLAN but another VLAN exists with a different link or ID. Recreating"
#                     )
#                     self.netlink.link("del", ifname=self.config.name)
#             else:
#                 logger.error(
#                     f"Interface {self.config.name} is defined as a VLAN but another interface with the same name already exists"
#                 )
#                 return

#         if not self.vxlan:
#             self.netlink.link("add", ifname=self.config.name, kind="vxlan")
#             await self.set_attrs()

#     async def stop(self):
#         if self.vxlan:
#             self.netlink.link("del", ifname=self.config.name)
#             self.vxlan = None

#     async def handle_config_change(
#         self, config: interface_pb2.InterfaceConfig, interfaces: list[NetlinkInterfaceAddEvent]
#     ):
#         old_config = self.config
#         self.config = config

#         if not self.vxlan:
#             return

#         reset_attrs = False

#         if old_config.bridge.ageing_time != config.bridge.ageing_time:
#             reset_attrs = True
#         if old_config.bridge.forward_delay != config.bridge.forward_delay:
#             reset_attrs = True
#         if old_config.bridge.hello_time != config.bridge.hello_time:
#             reset_attrs = True
#         if old_config.bridge.max_age != config.bridge.max_age:
#             reset_attrs = True
#         if old_config.bridge.stp != config.bridge.stp:
#             reset_attrs = True
#         if old_config.bridge.priority != config.bridge.priority:
#             reset_attrs = True
#         if old_config.bridge.vlan_filtering != config.bridge.vlan_filtering:
#             reset_attrs = True
#         if old_config.bridge.default_pvid != config.bridge.default_pvid:
#             reset_attrs = True

#         if self.vxlan and reset_attrs:
#             await self.set_attrs()

#     async def handle_interface_add(self, interface: NetlinkInterfaceAddEvent):
#         if not self.vxlan and interface.ifname == self.config.name:
#             if interface.kind == "bridge":
#                 self.vxlan = interface
#                 await self.set_attrs()
#             else:
#                 logger.error(
#                     f"Interface {self.config.name} is defined as a bridge but another interface with the same name appeared"
#                 )

#     async def handle_interface_remove(self, interface: NetlinkInterfaceDeleteEvent):
#         if self.vxlan and interface.ifname == self.config.name:
#             self.vxlan = None

#     def vxlan_interface_matches_config(self, interface: NetlinkInterfaceAddEvent):
#         if interface.ifname != self.config.name:
#             return False
#         if interface.kind != self.config.name:
#             return False

#         return True

#     async def set_attrs(self):
#         args = {}

#         if self.config.bridge.ageing_time:
#             args["br_ageing_time"] = self.config.bridge.ageing_time
#         if self.config.bridge.forward_delay:
#             args["br_forward_delay"] = self.config.bridge.forward_delay
#         if self.config.bridge.hello_time:
#             args["br_hello_time"] = self.config.bridge.hello_time
#         if self.config.bridge.max_age:
#             args["br_max_age"] = self.config.bridge.max_age
#         args["br_stp_state"] = self.config.bridge.stp
#         if self.config.bridge.priority:
#             args["br_priority"] = self.config.bridge.priority
#         args["br_vlan_filtering"] = self.config.bridge.vlan_filtering
#         if self.config.bridge.default_pvid:
#             args["br_vlan_default_pvid"] = self.config.bridge.default_pvid

#         if args:
#             self.netlink.link("set", ifname=self.config.name, **args)

#     @property
#     def dependent_interfaces(self):
#         if self.config and self.config.vxlan.interface:
#             return [self.config.vxlan.interface]
#         return []

#     def on_dependent_interface_add(self, interface_event):
#         if not self.ifindex:
#             self.apply()

#     def create(self):
#         if self.config.vxlan.remote and self.config.vxlan.group:
#             raise InvalidConfig("VXLAN cannot have a remote and a group address")

#         args = {}

#         if self.config.vxlan.interface:
#             interface_ifindex = self.provider.get_ifindex(self.config.vxlan.interface)
#             if not interface_ifindex:
#                 # Base interface does not yet exist
#                 return
#             args["vxlan_link"] = interface_ifindex

#         if self.config.vxlan.port:
#             args["vxlan_port"] = self.config.vxlan.port

#         if self.config.vxlan.group:
#             args["vxlan_group"] = self.config.vxlan.group

#         if self.config.vxlan.remote:
#             args["vxlan_remote"] = self.config.vxlan.remote

#         if self.config.vxlan.local:
#             args["vxlan_local"] = self.config.vxlan.local

#         if self.config.vxlan.ttl:
#             args["vxlan_ttl"] = self.config.vxlan.ttl

#         if self.config.vxlan.vni:
#             args["vxlan_vni"] = self.config.vxlan.vni

#         try:
#             self.link("add", ifname=self.name, kind="vxlan", **args)
#         except NetlinkError as e:
#             if e.code != errno.EEXIST:
#                 raise

#         self.update_endpoints()

#     def update_endpoints(self):
#         pass


# class SITInterface(BaseInterface):
#     def create(self):
#         if not self.config.sit.remote:
#             raise InvalidConfig("SIT interface requires remote address")

#         if not self.config.sit.local:
#             raise InvalidConfig("SIT interface requires local address")

#         remote = ipaddress.ip_address(self.config.sit.remote)
#         local = ipaddress.ip_address(self.config.sit.local)

#         if remote.version != 4:
#             raise InvalidConfig("SIT interface remote address must be IPv4")

#         if local.version != 4:
#             raise InvalidConfig("SIT interface local address must be IPv4")

#         ttl = self.config.sit.ttl if self.config.sit.ttl else 255

#         args = {
#             "sit_remote": str(remote),
#             "sit_local": str(local),
#             "sit_ttl": ttl,
#         }
#         try:
#             self.link("add", ifname=self.name, kind="sit", **args)
#         except NetlinkError as e:
#             if e.code != errno.EEXIST:
#                 raise
