"""
routesia/interface/cli.py - Routesia interface commands
"""

from ipaddress import IPv4Address, ip_address

from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import UInt8, UInt16, UInt32
from routesia.rpcclient import RPCClient
from routesia.schema.v2 import interface_pb2
from routesia.service import Provider


class InterfaceCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("interface")
        self.rpc = rpc

        self.cli.add_argument_completer(
            "system-interface", self.complete_system_interface
        )
        self.cli.add_argument_completer(
            "unconfigured-interface", self.complete_unconfigured_interface
        )
        self.cli.add_argument_completer(
            "interface", self.complete_interface, namespace=None
        )
        self.cli.add_argument_completer("type", self.complete_type)
        self.cli.add_argument_completer(
            "link.addrgenmode", self.complete_link_addrgenmode
        )

        self.cli.add_command("interface show", self.show_interface)
        self.cli.add_command(
            "interface show :interface!system-interface", self.show_interface
        )
        self.cli.add_command(
            "interface config list @interface", self.show_configured_interface
        )
        self.cli.add_command(
            "interface config add "
            ":interface!unconfigured-interface "
            "@type!type "
            "@link.up!bool "
            "@link.noarp!bool "
            "@link.txqueuelen "
            "@link.mtu "
            "@link.address "
            "@link.broadcast "
            "@link.master "
            "@link.addrgenmode "
            "@link.token "
            "@bridge.ageing_time "
            "@bridge.forward_delay "
            "@bridge.hello_time "
            "@bridge.max_age "
            "@bridge.stp!bool "
            "@bridge.priority "
            "@bridge.vlan_filtering!bool "
            "@bridge.default_pvid "
            "@vlan.trunk!bool "
            "@vlan.id "
            "@vlan.gvrp!bool "
            "@vlan.mvrp!bool "
            "@sit.remote "
            "@sit.local "
            "@sit.ttl "
            "@vxlan.port "
            "@vxlan.group "
            "@vxlan.remote "
            "@vxlan.local "
            "@vxlan.interface!interface "
            "@vxlan.ttl "
            "@vxlan.vni "
            "@vxlan.endpoints",
            self.add_configured_interface,
        )
        self.cli.add_command(
            "interface config update "
            ":interface "
            "@type "
            "@link.up!bool "
            "@link.noarp!bool "
            "@link.txqueuelen "
            "@link.mtu "
            "@link.address "
            "@link.broadcast "
            "@link.master "
            "@link.addrgenmode "
            "@link.token "
            "@bridge.ageing_time "
            "@bridge.forward_delay "
            "@bridge.hello_time "
            "@bridge.max_age "
            "@bridge.stp!bool "
            "@bridge.priority "
            "@bridge.vlan_filtering!bool "
            "@bridge.default_pvid "
            "@vlan.trunk!bool "
            "@vlan.id "
            "@vlan.gvrp!bool "
            "@vlan.mvrp!bool "
            "@sit.remote "
            "@sit.local "
            "@sit.ttl "
            "@vxlan.port "
            "@vxlan.group "
            "@vxlan.remote "
            "@vxlan.local "
            "@vxlan.interface!interface "
            "@vxlan.ttl "
            "@vxlan.vni "
            "@vxlan.endpoints",
            self.update_configured_interface,
        )
        self.cli.add_command(
            "interface config delete :interface", self.delete_interface
        )

    async def complete_system_interface(self):
        completions = []
        interfaces = await self.rpc.request("interface/list")
        for interface in interfaces.interface:
            completions.append(interface.name)
        return completions

    async def complete_interface(self):
        completions = []
        interfaces = await self.rpc.request("interface/config/list")
        for interface in interfaces.interface:
            completions.append(interface.name)
        return completions

    async def complete_unconfigured_interface(self):
        system_interfaces = set(await self.complete_system_interface())
        configured_interfaces = set(await self.complete_interface())
        return list(system_interfaces - configured_interfaces)

    async def complete_type(self):
        return interface_pb2.InterfaceType.keys()

    async def complete_link_addrgenmode(self):
        return interface_pb2.InterfaceLink.AddrGenMode.keys()

    async def show_interface(self, interface: str | None = None):
        interfaces = await self.rpc.request("interface/list")
        if interface is not None:
            for interface_object in interfaces.interface:
                if interface_object.name == interface:
                    return interface_object
            raise InvalidArgument("No such interface: %s" % interface)
        return interfaces

    async def show_configured_interface(self, interface=None):
        interfaces = await self.rpc.request("interface/config/list")
        if interface:
            for interface_object in interfaces.interface:
                if interface_object.name == interface:
                    return interface_object
            raise InvalidArgument("No such interface: %s" % interface)
        return interfaces

    def set_vxlan_enpoints(config: interface_pb2.InterfaceConfig, endpoints: str):
        del config.vxlan.endpoint[:]
        for endpoint_definition in endpoints.split(","):
            try:
                address, port, vni = endpoint_definition.split(";")
            except ValueError:
                raise InvalidArgument(
                    "VXLAN endpoints must be expressed as address:port:vni"
                )
            try:
                ip_address(address)
            except ValueError:
                raise InvalidArgument(
                    f"VXLAN endpoint address {address} is not a valid address"
                )
            try:
                port = UInt16(port)
            except ValueError as e:
                raise InvalidArgument(str(e))
            try:
                vni = UInt32(vni)
            except ValueError as e:
                raise InvalidArgument(str(e))
            if vni > 16777216:
                raise InvalidArgument("vxlan endpoint vni must be less than 16777216")

            endpoint = config.vxlan.endpoint.add()
            endpoint.remote = address
            endpoint.port = port
            endpoint.vni = vni

    async def add_configured_interface(
        self,
        interface: str,
        type: str = "ETHERNET",
        link_up: bool = True,
        link_noarp: bool = False,
        link_txqueuelen: UInt32 = None,
        link_mtu: UInt32 = None,
        link_address: str = None,
        link_broadcast: str = None,
        link_master: str = None,
        link_addrgenmode: str = None,
        link_token: str = None,
        bridge_ageing_time: UInt32 = None,
        bridge_forward_delay: UInt32 = None,
        bridge_hello_time: UInt32 = None,
        bridge_max_age: UInt32 = None,
        bridge_stp: bool = False,
        bridge_priority: UInt32 = None,
        bridge_vlan_filtering: bool = False,
        bridge_default_pvid: UInt32 = None,
        vlan_trunk: str = None,
        vlan_id: UInt32 = None,
        vlan_gvrp: bool = False,
        vlan_mvrp: bool = False,
        sit_remote: IPv4Address = None,
        sit_local: IPv4Address = None,
        sit_ttl: UInt8 = None,
        vxlan_port: UInt16 = None,
        vxlan_group: IPv4Address = None,
        vxlan_remote: IPv4Address = None,
        vxlan_local: IPv4Address = None,
        vxlan_interface: str = None,
        vxlan_ttl: UInt8 = None,
        vxlan_vni: UInt32 = None,
        vxlan_endpoints: str = None,
    ):
        config = interface_pb2.InterfaceConfig()
        config.name = interface
        config.type = interface_pb2.InterfaceType.Value(type)
        config.link.up = link_up
        config.link.noarp = link_noarp
        if link_txqueuelen is not None:
            config.link.txqueuelen = link_txqueuelen
        if link_mtu is not None:
            config.link.mtu = link_mtu
        if link_address is not None:
            config.link.address = link_address
        if link_broadcast is not None:
            config.link.broadcast = link_broadcast
        if link_master is not None:
            config.link.master = link_master
        if link_addrgenmode is not None:
            config.link.addrgenmode = interface_pb2.InterfaceLink.AddrGenMode.Value(
                link_addrgenmode
            )
        if link_token is not None:
            if config.link.noarp:
                raise InvalidArgument("link.token is not valid when link.noarp is set")
            config.link.token = link_token
        if bridge_ageing_time is not None:
            config.bridge.ageing_time = bridge_ageing_time
        if bridge_forward_delay is not None:
            config.bridge.forward_delay = bridge_forward_delay
        if bridge_hello_time is not None:
            config.bridge.hello_time = bridge_hello_time
        if bridge_max_age is not None:
            config.bridge.max_age = bridge_max_age
        config.bridge.stp = bridge_stp
        if bridge_priority is not None:
            config.bridge.priority = bridge_priority
        config.bridge.vlan_filtering = bridge_vlan_filtering
        if bridge_default_pvid is not None:
            config.bridge.default_pvid = bridge_default_pvid
        if vlan_trunk is not None:
            config.vlan.trunk = vlan_trunk
        if vlan_id is not None:
            if not 1 <= vlan_id <= 4094:
                raise InvalidArgument("vlan.id must be between 1 and 4094 inclusive")
            config.vlan.id = vlan_id
        config.vlan.gvrp = vlan_gvrp
        config.vlan.mvrp = vlan_mvrp
        if sit_remote is not None:
            config.sit.remote = str(sit_remote)
        if sit_local is not None:
            config.sit.local = str(sit_local)
        if sit_ttl is not None:
            if sit_ttl < 1:
                raise InvalidArgument("sit.ttl must be greater than 0")
            config.sit.ttl = sit_ttl
        if vxlan_port is not None:
            config.vxlan.port = vxlan_port
        if vxlan_group is not None:
            config.vxlan.group = str(vxlan_group)
        if vxlan_remote is not None:
            config.vxlan.remote = str(vxlan_remote)
        if vxlan_local is not None:
            config.vxlan.local = str(vxlan_local)
        if vxlan_interface is not None:
            config.vxlan.interface = vxlan_interface
        if vxlan_ttl is not None:
            if vxlan_ttl < 1:
                raise InvalidArgument("vxlan.ttl must be greater than 1")
            config.vxlan.ttl = vxlan_ttl
        if vxlan_vni is not None:
            if vxlan_vni < 16777216:
                raise InvalidArgument("vxlan.vni must be less than 16777216")
            config.vxlan.vni = vxlan_vni
        if vxlan_endpoints is not None:
            self.set_vxlan_enpoints(config, vxlan_endpoints)

        await self.rpc.request("interface/config/add", config)

    async def update_configured_interface(
        self,
        interface: str,
        type=None,
        link_up: bool = None,
        link_noarp: bool = None,
        link_txqueuelen: UInt32 = None,
        link_mtu: UInt32 = None,
        link_address: str = None,
        link_broadcast: str = None,
        link_master: str = None,
        link_addrgenmode: str = None,
        link_token: str = None,
        bridge_ageing_time: UInt32 = None,
        bridge_forward_delay: UInt32 = None,
        bridge_hello_time: UInt32 = None,
        bridge_max_age: UInt32 = None,
        bridge_stp: bool = None,
        bridge_priority: UInt32 = None,
        bridge_vlan_filtering: bool = None,
        bridge_default_pvid: UInt32 = None,
        vlan_trunk: str = None,
        vlan_id: UInt32 = None,
        vlan_gvrp: bool = None,
        vlan_mvrp: bool = None,
        sit_remote: IPv4Address = None,
        sit_local: IPv4Address = None,
        sit_ttl: UInt8 = None,
        vxlan_port: UInt16 = None,
        vxlan_group: IPv4Address = None,
        vxlan_remote: IPv4Address = None,
        vxlan_local: IPv4Address = None,
        vxlan_interface: str = None,
        vxlan_ttl: UInt8 = None,
        vxlan_vni: UInt32 = None,
        vxlan_endpoints: str = None,
    ):
        interfaces = await self.rpc.request("interface/config/list")
        config = None
        for config in interfaces.interface:
            if config.name == interface:
                break
        if not config:
            raise InvalidArgument(f"No such interface: {interface}")
        if type is not None:
            config.type = interface_pb2.InterfaceType.Value(type)
        if link_up is not None:
            config.link.up = link_up
        if link_noarp is not None:
            config.link.noarp = link_noarp
        if link_txqueuelen is not None:
            config.link.txqueuelen = link_txqueuelen
        if link_mtu is not None:
            config.link.mtu = link_mtu
        if link_address is not None:
            config.link.address = link_address
        if link_broadcast is not None:
            config.link.broadcast = link_broadcast
        if link_master is not None:
            config.link.master = link_master
        if link_addrgenmode is not None:
            config.link.addrgenmode = interface_pb2.InterfaceLink.AddrGenMode.Value(
                link_addrgenmode
            )
        if link_token is not None:
            config.link.token = link_token
        if bridge_ageing_time is not None:
            config.bridge.ageing_time = bridge_ageing_time
        if bridge_forward_delay is not None:
            config.bridge.forward_delay = bridge_forward_delay
        if bridge_hello_time is not None:
            config.bridge.hello_time = bridge_hello_time
        if bridge_max_age is not None:
            config.bridge.max_age = bridge_max_age
        if bridge_stp is not None:
            config.bridge.stp = bridge_stp
        if bridge_priority is not None:
            config.bridge.priority = bridge_priority
        if bridge_vlan_filtering is not None:
            config.bridge.vlan_filtering = bridge_vlan_filtering
        if bridge_default_pvid is not None:
            config.bridge.default_pvid = bridge_default_pvid
        if vlan_trunk is not None:
            config.vlan.trunk = vlan_trunk
        if vlan_id is not None:
            if not 1 <= vlan_id <= 4094:
                raise InvalidArgument("vlan.id must be between 1 and 4094 inclusive")
            config.vlan.id = vlan_id
        if vlan_gvrp is not None:
            config.vlan.gvrp = vlan_gvrp
        if vlan_mvrp is not None:
            config.vlan.mvrp = vlan_mvrp
        if sit_remote is not None:
            config.sit.remote = str(sit_remote)
        if sit_local is not None:
            config.sit.local = str(sit_local)
        if sit_ttl is not None:
            if sit_ttl < 1:
                raise InvalidArgument("sit.ttl must be greater than 0")
            config.sit.ttl = sit_ttl
        if vxlan_port is not None:
            config.vxlan.port = vxlan_port
        if vxlan_group is not None:
            config.vxlan.group = str(vxlan_group)
        if vxlan_remote is not None:
            config.vxlan.remote = str(vxlan_remote)
        if vxlan_local is not None:
            config.vxlan.local = str(vxlan_local)
        if vxlan_interface is not None:
            config.vxlan.interface = vxlan_interface
        if vxlan_ttl is not None:
            if vxlan_ttl < 1:
                raise InvalidArgument("vxlan.ttl must be greater than 1")
            config.vxlan.ttl = vxlan_ttl
        if vxlan_vni is not None:
            if vxlan_vni < 16777216:
                raise InvalidArgument("vxlan.vni must be less than 16777216")
            config.vxlan.vni = vxlan_vni
        if vxlan_endpoints is not None:
            self.set_vxlan_enpoints(config, vxlan_endpoints)

        await self.rpc.request("interface/config/update", config)

    async def delete_interface(self, interface):
        config = interface_pb2.InterfaceConfig()
        config.name = interface
        await self.rpc.request("interface/config/delete", config)
