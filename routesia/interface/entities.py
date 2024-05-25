"""
routesia/interface/entities.py - Interface entities
"""

import errno
import ipaddress
import logging
from pyroute2.netlink.exceptions import NetlinkError

from routesia.config.provider import InvalidConfig
from routesia.dhcp.client.events import DHCPv4LeasePreinit
from routesia.interface import interface_flags
from routesia.interface import interface_types
from routesia.schema.v1 import interface_pb2


logger = logging.getLogger("interface")


class InterfaceEntity:
    def __init__(self, provider, name, config=None):
        super().__init__()
        self.config = config
        self.provider = provider
        self.name = name
        self.iproute = provider.iproute
        self.ifindex = None
        self.carrier = False
        self.state = interface_pb2.InterfaceLink()
        self.dynamic_config = None

    @property
    def dependent_interfaces(self):
        if self.config and self.config.link.master:
            return [self.config.link.master]
        return []

    def update_state(self, event):
        link = event.message
        new = self.ifindex is None
        self.ifindex = link["index"]
        if "IFLA_CARRIER" in event.attrs:
            self.carrier = bool(event.attrs["IFLA_CARRIER"])

        self.state.up = link["flags"] & interface_flags.IFF_UP
        self.state.noarp = link["flags"] & interface_flags.IFF_NOARP
        if "IFLA_TXQLEN" in event.attrs:
            self.state.txqueuelen = event.attrs["IFLA_TXQLEN"]
        if "IFLA_MTU" in event.attrs:
            self.state.mtu = event.attrs["IFLA_MTU"]
        if "IFLA_ADDRESS" in event.attrs:
            self.state.address = event.attrs["IFLA_ADDRESS"]
        if "IFLA_BROADCAST" in event.attrs:
            self.state.broadcast = event.attrs["IFLA_BROADCAST"]

        if "IFLA_AF_SPEC" in event.attrs:
            af_attrs = dict(event.attrs["IFLA_AF_SPEC"]["attrs"])
            if "AF_INET6" in af_attrs:
                af_inet6_attrs = dict(af_attrs["AF_INET6"]["attrs"])
                self.state.addrgenmode = af_inet6_attrs["IFLA_INET6_ADDR_GEN_MODE"]
                self.state.token = af_inet6_attrs["IFLA_INET6_TOKEN"]

    def start(self):
        self.apply()

    def stop(self):
        self.remove()

    def on_interface_remove(self):
        self.state.Clear()
        self.ifindex = None

    def on_dependent_interface_add(self, interface_event):
        self.apply()

    def on_dependent_interface_remove(self, interface_event):
        self.apply()

    def on_config_change(self, config):
        old_config = self.config
        self.config = config
        if old_config is None:
            self.apply(new=True)
        elif old_config.SerializeToString() != self.config.SerializeToString():
            self.apply()

    def on_config_removed(self):
        self.config = None
        self.remove()

    async def handle_dhcp_lease_preinit(self, event: DHCPv4LeasePreinit):
        if not self.state.up:
            self.link("set", state="up")

    def link(self, *args, **kwargs):
        if "add" not in args:
            kwargs["index"] = self.ifindex
        return self.iproute.iproute.link(*args, **kwargs)

    def create(self):
        "Create interface. Only implemented for virtual interfaces"
        pass

    def remove(self):
        "Remove interface. Only implemented for virtual interfaces"
        pass

    def get_link_config_args(self):
        args = {}
        af_spec = []
        af_inet6 = []

        if self.config and self.config.link:
            for field, value in self.config.link.ListFields():
                if field.name == "up":
                    args["state"] = "up" if value else "down"
                elif field.name == "noarp":
                    args["arp"] = not value
                elif field.name == "txqueuelen":
                    args["txqlen"] = value
                elif field.name == "mtu" and value:
                    args["mtu"] = value
                elif field.name == "address" and value:
                    args["address"] = value
                elif field.name == "broadcast" and value:
                    args["broadcast"] = value
                elif field.name == "master":
                    args["master"] = self.provider.get_ifindex(value)
                elif field.name == "addrgenmode":
                    af_inet6.append(("IFLA_INET6_ADDR_GEN_MODE", value))
                elif field.name == "token" and value:
                    af_inet6.append(("IFLA_INET6_TOKEN", value))
                else:
                    args[field.name] = value
            if af_inet6:
                af_spec.append(("AF_INET6", {"attrs": af_inet6}))
            if af_spec:
                args["IFLA_AF_SPEC"] = {"attrs": af_spec}

        if self.dynamic_config:
            args.update(self.dynamic_config)

        return args

    def apply_link_config(self):
        if not self.provider.running:
            return

        args = self.get_link_config_args()
        if args:
            logger.info("Applying link config to %s: %s" % (self.name, args))
            self.link("set", **args)

    def apply(self, new=False):
        if self.config is not None:
            self.create()
            if self.ifindex:
                self.apply_link_config()
            if new:
                self.flush_addresses()

    def flush_addresses(self):
        if self.ifindex is not None:
            self.iproute.iproute.flush_addr(ifindex=self.ifindex)

    def to_message(self, message):
        "Set message parameters from entity state"
        message.name = self.name
        message.link.CopyFrom(self.state)
        if self.config:
            message.config.CopyFrom(self.config)

    def set_dynamic_config(self, config):
        self.dynamic_config = config
        self.apply_link_config()


class EthernetInterface(InterfaceEntity):
    pass


class VirtualInterface(InterfaceEntity):
    """
    Base class for virtual interfaces that are created and removed
    """
    def remove(self):
        if self.ifindex is not None:
            try:
                self.link("del", ifindex=self.ifindex)
            except NetlinkError as e:
                if e.code != errno.ENODEV:
                    raise


class BridgeInterface(VirtualInterface):
    def create(self):
        try:
            self.link("add", ifname=self.name, kind="bridge")
        except NetlinkError as e:
            if e.code != errno.EEXIST:
                raise

    def get_link_config_args(self):
        args = super().get_link_config_args()

        if self.config and self.config.bridge:
            for field, value in self.config.bridge.ListFields():
                if field.name == "stp":
                    args["br_stp_state"] = value
                elif field.name == "default_pvid":
                    args["br_vlan_default_pvid"] = value
                else:
                    args["br_%s" % field.name] = value

        return args


class VLANInterface(VirtualInterface):
    @property
    def dependent_interfaces(self):
        if self.config:
            return [self.config.vlan.trunk]
        return []

    def on_dependent_interface_add(self, interface_event):
        if not self.ifindex:
            self.apply()

    def create(self):
        if not (self.config.vlan and self.config.vlan.id and self.config.vlan.trunk):
            raise InvalidConfig(
                "Interface is of type vlan but does not have a VLAN ID or trunk set"
            )

        trunk_ifindex = self.provider.get_ifindex(self.config.vlan.trunk)
        if not trunk_ifindex:
            # Trunk interface does not yet exist
            return

        args = {
            "vlan_id": self.config.vlan.id,
            "link": trunk_ifindex,
        }

        vlan_flags = []
        if self.config.vlan.gvrp:
            vlan_flags.append("gvrp")
        if self.config.vlan.mvrp:
            vlan_flags.append("mvrp")

        if vlan_flags:
            args["vlan_flags"] = vlan_flags

        try:
            self.link("add", ifname=self.name, kind="vlan", **args)
        except NetlinkError as e:
            if e.code != errno.EEXIST:
                raise


class VXLANInterface(VirtualInterface):
    @property
    def dependent_interfaces(self):
        if self.config and self.config.vxlan.interface:
            return [self.config.vxlan.interface]
        return []

    def on_dependent_interface_add(self, interface_event):
        if not self.ifindex:
            self.apply()

    def create(self):
        if self.config.vxlan.remote and self.config.vxlan.group:
            raise InvalidConfig(
                "VXLAN cannot have a remote and a group address"
            )

        args = {}

        if self.config.vxlan.interface:
            interface_ifindex = self.provider.get_ifindex(self.config.vxlan.interface)
            if not interface_ifindex:
                # Base interface does not yet exist
                return
            args["vxlan_link"] = interface_ifindex

        if self.config.vxlan.port:
            args["vxlan_port"] = self.config.vxlan.port

        if self.config.vxlan.group:
            args["vxlan_group"] = self.config.vxlan.group

        if self.config.vxlan.remote:
            args["vxlan_remote"] = self.config.vxlan.remote

        if self.config.vxlan.local:
            args["vxlan_local"] = self.config.vxlan.local

        if self.config.vxlan.ttl:
            args["vxlan_ttl"] = self.config.vxlan.ttl

        if self.config.vxlan.vni:
            args["vxlan_vni"] = self.config.vxlan.vni

        try:
            self.link("add", ifname=self.name, kind="vxlan", **args)
        except NetlinkError as e:
            if e.code != errno.EEXIST:
                raise

        self.update_endpoints()

    def update_endpoints(self):
        pass


class InfinibandInterface(InterfaceEntity):
    pass


class IPIPInterface(VirtualInterface):
    pass


class IPIP6Interface(VirtualInterface):
    pass


class LoopbackInterface(InterfaceEntity):
    pass


class SITInterface(VirtualInterface):
    def create(self):
        if not self.config.sit.remote:
            raise InvalidConfig("SIT interface requires remote address")

        if not self.config.sit.local:
            raise InvalidConfig("SIT interface requires local address")

        remote = ipaddress.ip_address(self.config.sit.remote)
        local = ipaddress.ip_address(self.config.sit.local)

        if remote.version != 4:
            raise InvalidConfig("SIT interface remote address must be IPv4")

        if local.version != 4:
            raise InvalidConfig("SIT interface local address must be IPv4")

        ttl = self.config.sit.ttl if self.config.sit.ttl else 255

        args = {
            "sit_remote": str(remote),
            "sit_local": str(local),
            "sit_ttl": ttl,
        }
        try:
            self.link("add", ifname=self.name, kind="sit", **args)
        except NetlinkError as e:
            if e.code != errno.EEXIST:
                raise


class GREInterface(VirtualInterface):
    pass


class WiFiInterface(InterfaceEntity):
    pass


# Interface class map indexed by type and kind
#
INTERFACE_TYPE_ENTITY_MAP = {
    (interface_types.ARPHRD_ETHER, None): EthernetInterface,
    (interface_types.ARPHRD_ETHER, "bridge"): BridgeInterface,
    (interface_types.ARPHRD_ETHER, "vlan"): VLANInterface,
    (interface_types.ARPHRD_ETHER, "vxlan"): VXLANInterface,
    # (interface_types.ARPHRD_INFINIBAND, None): InfinibandInterface,
    # (interface_types.ARPHRD_TUNNEL, None): IPIPInterface,
    # (interface_types.ARPHRD_TUNNEL6, None): IPIP6Interface,
    (interface_types.ARPHRD_LOOPBACK, None): LoopbackInterface,
    (interface_types.ARPHRD_SIT, None): SITInterface,
    # (interface_types.ARPHRD_IPGRE, None): GREInterface,
    # (interface_types.ARPHRD_IEEE80211, None): WiFiInterface,
}

# Interface class map indexed by InterfaceConfig type
#
INTERFACE_CONFIG_TYPE_ENTITY_MAP = {
    interface_pb2.ETHERNET: EthernetInterface,
    interface_pb2.BRIDGE: BridgeInterface,
    interface_pb2.VLAN: VLANInterface,
    interface_pb2.VXLAN: VXLANInterface,
    # interface_pb2.INFINIBAND: InfinibandInterface,
    # interface_pb2.IPIP: IPIPInterface,
    # interface_pb2.IPIP6: IPIP6Interface,
    interface_pb2.LOOPBACK: LoopbackInterface,
    interface_pb2.SIT: SITInterface,
    # interface_pb2.GRE: GREInterface,
    # interface_pb2.WIFI: WiFiInterface,
}
