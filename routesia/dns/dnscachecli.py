"""
routesia/dns/cache/cli.py - Routesia DNS cache commands
"""

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import UInt16, UInt32
from routesia.rpcclient import RPCClient
from routesia.service import Provider
from routesia.schema.v2 import dns_cache_pb2


class DNSCacheCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("dns-cache")
        self.rpc = rpc

        self.cli.add_argument_completer("listen-address", self.complete_listen_address)
        self.cli.add_argument_completer("listen-port", self.complete_listen_port)
        self.cli.add_argument_completer("action", self.complete_action)
        self.cli.add_argument_completer(
            "forward-zone-name", self.complete_forward_zone_name
        )
        self.cli.add_argument_completer(
            "forward-zone-address", self.complete_forward_zone_address
        )
        self.cli.add_argument_completer("zone-type", self.complete_zone_type)
        self.cli.add_argument_completer(
            "local-zone-name", self.complete_local_zone_name
        )
        self.cli.add_argument_completer(
            "local-zone-ipam-network", self.complete_local_zone_ipam_network
        )
        self.cli.add_argument_completer("zone-data-type", self.complete_record_type)
        self.cli.add_argument_completer(
            "local-zone-record-name", self.complete_local_zone_record_name
        )
        self.cli.add_argument_completer(
            "local-zone-record-type", self.complete_local_zone_record_type
        )
        self.cli.add_argument_completer(
            "local-zone-record-data", self.complete_local_zone_record_data
        )

        self.cli.add_command("dns cache config show", self.show_config)
        self.cli.add_command(
            "dns cache config update @enabled @tls-upstream @ttl", self.update_config
        )

        self.cli.add_command(
            "dns cache config listen-address add :listen-address! @listen-port!",
            self.add_listen_address,
        )
        self.cli.add_command(
            "dns cache config listen-address remove :listen-address @listen-port",
            self.remove_listen_address,
        )

        self.cli.add_command(
            "dns cache config access-control-rule add :priority! :network! :action",
            self.add_access_rule,
        )
        self.cli.add_command(
            "dns cache config access-control-rule remove :priority! :network! :action",
            self.remove_access_rule,
        )

        self.cli.add_command(
            "dns cache config forward-zone add :forward-zone-name!",
            self.add_forward_zone,
        )
        self.cli.add_command(
            "dns cache config forward-zone update :forward-zone-name @forward-tls!bool",
            self.update_forward_zone,
        )
        self.cli.add_command(
            "dns cache config forward-zone remove :forward-zone-name",
            self.remove_forward_zone,
        )

        self.cli.add_command(
            "dns cache config forward-zone forward-address add :forward-zone-name :forward-zone-address! @port @host",
            self.add_forward_zone_forward_address,
        )
        self.cli.add_command(
            "dns cache config forward-zone forward-address update :forward-zone-name :forward-zone-address @port @host",
            self.update_forward_zone_forward_address,
        )
        self.cli.add_command(
            "dns cache config forward-zone forward-address remove :forward-zone-name :forward-zone-address",
            self.remove_forward_zone_forward_address,
        )

        self.cli.add_command(
            "dns cache config local-zone add :local-zone-name! @zone-type @ttl @use-ipam",
            self.add_local_zone,
        )
        self.cli.add_command(
            "dns cache config local-zone update :local-zone-name @zone-type @ttl @use-ipam",
            self.update_local_zone,
        )
        self.cli.add_command(
            "dns cache config local-zone remove :local-zone-name",
            self.remove_local_zone,
        )

        self.cli.add_command(
            "dns cache config local-zone ipam-network add :local-zone-name :local-zone-ipam-network!",
            self.add_local_zone_ipam_network,
        )
        self.cli.add_command(
            "dns cache config local-zone ipam-network remove :local-zone-name :local-zone-ipam-network",
            self.remove_local_zone_ipam_network,
        )

        self.cli.add_command(
            "dns cache config local-zone local-data add :local-zone-name :record-name :record-type :record-data @ttl",
            self.add_local_zone_local_data,
        )
        self.cli.add_command(
            "dns cache config local-zone local-data update :local-zone-name :record-name!local-zone-record-name :record-type!local-zone-record-type :record-data!local-zone-record-data @ttl",
            self.update_local_zone_local_data,
        )
        self.cli.add_command(
            "dns cache config local-zone local-data remove :local-zone-name :record-name!local-zone-record-name :record-type!local-zone-record-type :record-data!local-zone-record-data",
            self.remove_local_zone_local_data,
        )

    async def complete_listen_address(self):
        completions = []
        config = await self.rpc.request("dns/cache/config/get")
        for listen_address in config.listen_address:
            completions.append(listen_address.address)
        return completions

    async def complete_listen_port(
        self, listen_address: IPv4Address | IPv6Address | None = None
    ):
        completions = []
        config = await self.rpc.request("dns/cache/config/get")
        if listen_address is not None:
            listen_address = str(listen_address)
        for address in config.listen_address:
            if listen_address is not None and address.address != listen_address:
                continue
            completions.append(str(address.port))
        return completions

    async def complete_action(self):
        return (
            dns_cache_pb2.DNSCacheAccessControlRule.DNSCacheAccessControlRuleAction.keys()
        )

    async def show_config(self) -> dns_cache_pb2.DNSCacheConfig:
        return await self.rpc.request("dns/cache/config/get")

    async def update_config(
        self, enabled: bool = None, tls_upstream: bool = None, ttl: UInt32 = None
    ):
        config = await self.rpc.request("dns/cache/config/get")
        if enabled is not None:
            config.enabled = enabled
        if tls_upstream is not None:
            config.tls_upstream = tls_upstream
        if ttl is not None:
            config.ttl = ttl
        await self.rpc.request("dns/cache/config/update", config)

    async def add_listen_address(
        self, listen_address: IPv4Address | IPv6Address, listen_port: UInt16 = 0
    ):
        config = await self.rpc.request("dns/cache/config/get")

        for address in config.listen_address:
            if address.address == listen_address and address.port == listen_port:
                raise InvalidArgument("Listen address already exists")

        address = config.listen_address.add()
        address.address = str(listen_address)
        address.port = listen_port
        await self.rpc.request("dns/cache/config/update", config)

    async def remove_listen_address(
        self,
        listen_address: IPv4Address | IPv6Address,
        listen_port: UInt16 = 0,
    ):
        address = str(listen_address)
        config = await self.rpc.request("dns/cache/config/get")
        for i, listen_address in enumerate(config.listen_address):
            if listen_address.address == address:
                if listen_address.port != listen_port:
                    continue
                del config.listen_address[i]
                break
        await self.rpc.request("dns/cache/config/update", config)

    async def add_access_rule(
        self,
        priority: UInt32,
        network: IPv4Network | IPv6Network,
        action: str,
    ):
        action = dns_cache_pb2.DNSCacheAccessControlRule.DNSCacheAccessControlRuleAction.Value(
            action
        )
        config = await self.rpc.request("dns/cache/config/get")

        for access_control_rule in config.access_control_rule:
            if (
                access_control_rule.priority == priority
                and access_control_rule.network == network
                and access_control_rule.action == action
            ):
                raise InvalidArgument(
                    "Access control rule %s %s %s already exists"
                    % (priority, network, action)
                )

        access_control_rule = config.access_control_rule.add()
        access_control_rule.priority = priority
        access_control_rule.network = str(network)
        access_control_rule.action = action

        await self.rpc.request("dns/cache/config/update", config)

    async def remove_access_rule(
        self,
        priority: UInt32,
        network: IPv4Network | IPv6Network,
        action: str,
    ):
        network = str(network)
        action = dns_cache_pb2.DNSCacheAccessControlRule.DNSCacheAccessControlRuleAction.Value(
            action
        )
        config = await self.rpc.request("dns/cache/config/get")

        for i, access_control_rule in enumerate(config.access_control_rule):
            if (
                access_control_rule.priority == priority
                and access_control_rule.network == str(network)
                and access_control_rule.action == action
            ):
                del config.access_control_rule[i]
                break

        await self.rpc.request("dns/cache/config/update", config)

    async def add_forward_zone(self, forward_zone_name: str, forward_tls: bool = False):
        config = await self.rpc.request("dns/cache/config/get")

        for forward_zone in config.forward_zone:
            if forward_zone.name == forward_zone_name:
                raise InvalidArgument(
                    "Forward zone %s already exists" % forward_zone_name
                )

        forward_zone = config.forward_zone.add()
        forward_zone.name = forward_zone_name
        forward_zone.forward_tls = forward_tls

        await self.rpc.request("dns/cache/config/update", config)

    async def complete_forward_zone_name(self):
        completions = []
        config = await self.rpc.request("dns/cache/config/get")
        for forward_zone in config.forward_zone:
            completions.append(forward_zone.name)
        return completions

    def get_forward_zone(self, config, name: str):
        for forward_zone in config.forward_zone:
            if forward_zone.name == name:
                return forward_zone
        raise InvalidArgument("Forward zone %s does not exist" % name)

    async def update_forward_zone(
        self, forward_zone_name: str, forward_tls: bool = None
    ):
        config = await self.rpc.request("dns/cache/config/get")

        zone = self.get_forward_zone(config, forward_zone_name)
        if forward_tls is not None:
            zone.forward_tls = forward_tls

        await self.rpc.request("dns/cache/config/update", config)

    async def remove_forward_zone(self, forward_zone_name: str):
        config = await self.rpc.request("dns/cache/config/get")

        for i, zone in enumerate(config.forward_zone):
            if zone.name == forward_zone_name:
                del config.forward_zone[i]
                break

        await self.rpc.request("dns/cache/config/update", config)

    async def add_forward_zone_forward_address(
        self,
        forward_zone_name: str,
        forward_zone_address: IPv4Address | IPv6Address,
        port: UInt16 | None = None,
        host: str | None = None,
    ):
        config = await self.rpc.request("dns/cache/config/get")
        zone = self.get_forward_zone(config, forward_zone_name)
        forward_zone_address = str(forward_zone_address)
        for address in zone.forward_address:
            if address.address == forward_zone_address:
                raise InvalidArgument(
                    "Address %s already exists in forward zone %s"
                    % (forward_zone_address, zone.name)
                )
        address = zone.forward_address.add()
        address.address = forward_zone_address
        if port is not None:
            address.port = port
        if host is not None:
            address.host = host
        await self.rpc.request("dns/cache/config/update", config)

    async def complete_forward_zone_address(self, forward_zone_name: str | None = None):
        completions = []
        if forward_zone_name is None:
            return completions
        config = await self.rpc.request("dns/cache/config/get")
        for zone in config.forward_zone:
            if zone.name == forward_zone_name:
                break
        else:
            return completions
        for forward_address in zone.forward_address:
            completions.append(forward_address.address)
        return completions

    async def update_forward_zone_forward_address(
        self,
        forward_zone_name: str,
        forward_zone_address: IPv4Address | IPv6Address,
        port: UInt16 | None = None,
        host: str | None = None,
    ):
        config = await self.rpc.request("dns/cache/config/get")
        zone = self.get_forward_zone(config, forward_zone_name)
        forward_zone_address = str(forward_zone_address)
        for address in zone.forward_address:
            if address.address == forward_zone_address:
                if port is not None:
                    address.port = port
                if host is not None:
                    address.host = host
                break
        await self.rpc.request("dns/cache/config/update", config)

    async def remove_forward_zone_forward_address(
        self,
        forward_zone_name: str,
        forward_zone_address: IPv4Address | IPv6Address,
    ):
        config = await self.rpc.request("dns/cache/config/get")
        zone = self.get_forward_zone(config, forward_zone_name)
        forward_zone_address = str(forward_zone_address)
        for i, address in enumerate(zone.forward_address):
            if address.address == forward_zone_address:
                del zone.forward_address[i]
                break
        await self.rpc.request("dns/cache/config/update", config)

    async def complete_zone_type(self):
        return dns_cache_pb2.DNSCacheLocalZone.DNSCacheLocalZoneType.keys()

    async def add_local_zone(
        self,
        local_zone_name: str,
        zone_type: str | None = None,
        ttl: UInt32 = 0,
        use_ipam: bool = False,
    ):

        config = await self.rpc.request("dns/cache/config/get")

        for local_zone in config.local_zone:
            if local_zone.name == local_zone_name:
                raise InvalidArgument("Local zone %s already exists" % local_zone_name)

        local_zone = config.local_zone.add()
        local_zone.name = local_zone_name
        if zone_type is not None:
            local_zone.type = dns_cache_pb2.DNSCacheLocalZone.DNSCacheLocalZoneType.Value(
                zone_type
            )
        local_zone.ttl = ttl
        local_zone.use_ipam = use_ipam

        await self.rpc.request("dns/cache/config/update", config)

    def get_local_zone(self, config, name: str):
        for local_zone in config.local_zone:
            if local_zone.name == name:
                return local_zone
        raise InvalidArgument("Local zone %s does not exist" % name)

    async def complete_local_zone_name(self):
        completions = []
        config = await self.rpc.request("dns/cache/config/get")
        for local_zone in config.local_zone:
            completions.append(local_zone.name)
        return completions

    async def update_local_zone(
        self,
        local_zone_name: str,
        zone_type: str | None = None,
        ttl: UInt32 | None = None,
        use_ipam: bool | None = None,
    ):
        config = await self.rpc.request("dns/cache/config/get")

        local_zone = self.get_local_zone(config, local_zone_name)

        if zone_type is not None:
            local_zone.type = dns_cache_pb2.DNSCacheLocalZone.DNSCacheLocalZoneType.Value(
                zone_type
            )
        if ttl is not None:
            local_zone.ttl = ttl
        if use_ipam is not None:
            local_zone.use_ipam = use_ipam

        await self.rpc.request("dns/cache/config/update", config)

    async def remove_local_zone(self, local_zone_name: str):
        config = await self.rpc.request("dns/cache/config/get")

        for i, local_zone in enumerate(config.local_zone):
            if local_zone.name == local_zone_name:
                del config.local_zone[i]
                break

        await self.rpc.request("dns/cache/config/update", config)

    async def add_local_zone_ipam_network(
        self, local_zone_name: str, local_zone_ipam_network: IPv4Network | IPv6Network
    ):
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        network = str(local_zone_ipam_network)
        for ipam_network in local_zone.ipam_network:
            if ipam_network == network:
                raise InvalidArgument(
                    "IPAM network %s already exists in local zone %s"
                    % (network, local_zone.name)
                )
        local_zone.ipam_network.append(network)
        await self.rpc.request("dns/cache/config/update", config)

    async def complete_local_zone_ipam_network(self, local_zone_name: str):
        completions = []
        if local_zone_name is None:
            return completions
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        for ipam_network in local_zone.ipam_network:
            completions.append(ipam_network)
        return completions

    async def remove_local_zone_ipam_network(
        self, local_zone_name: str, local_zone_ipam_network: IPv4Network | IPv6Network
    ):
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        network = str(local_zone_ipam_network)
        for i, ipam_network in enumerate(local_zone.ipam_network):
            if ipam_network == network:
                del local_zone.ipam_network[i]
                break
        await self.rpc.request("dns/cache/config/update", config)

    async def complete_record_type(self):
        return dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.keys()

    async def add_local_zone_local_data(
        self,
        local_zone_name: str,
        record_name: str,
        record_type: str,
        record_data: str,
        ttl: UInt32 = 0,
    ):
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        record_type = dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Value(
            record_type
        )
        for local_data in local_zone.local_data:
            if (
                local_data.name == record_name
                and local_data.type == record_type
                and local_data.data == record_data
            ):
                raise InvalidArgument(
                    "Local data %s %s %s already exists in local zone %s"
                    % (
                        record_name,
                        dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Name(
                            record_type
                        ),
                        record_data,
                        local_zone.name,
                    )
                )
        local_data = local_zone.local_data.add()
        local_data.name = record_name
        local_data.type = record_type
        local_data.data = record_data
        local_data.ttl = ttl
        await self.rpc.request("dns/cache/config/update", config)

    async def complete_local_zone_record_name(self, local_zone_name: str | None = None):
        completions = []
        if local_zone_name is None:
            return completions
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        for local_data in local_zone.local_data:
            completions.append(local_data.name)
        return completions

    async def complete_local_zone_record_type(
        self, local_zone_name: str | None = None, record_name: str | None = None
    ):
        completions = []
        if local_zone_name is None:
            return completions
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        for local_data in local_zone.local_data:
            if record_name is not None and local_data.name != record_name:
                continue
            completions.append(
                dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Name(
                    local_data.type
                )
            )
        return completions

    async def complete_local_zone_record_data(
        self,
        local_zone_name: str | None = None,
        record_name: str | None = None,
        record_type: str | None = None,
    ):
        completions = []
        if local_zone_name is None or record_type is None:
            return completions
        record_type = dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Value(
            record_type
        )
        config = await self.rpc.request("dns/cache/config/get")
        local_zone = self.get_local_zone(config, local_zone_name)
        for local_data in local_zone.local_data:
            if record_name is not None and local_data.name != record_name:
                continue
            if record_type is not None and local_data.type != record_type:
                continue
            completions.append(local_data.data)
        return completions

    async def update_local_zone_local_data(
        self,
        local_zone_name: str,
        record_name: str,
        record_type: str,
        record_data: str | None = None,
        ttl: UInt32 | None = None,
    ):
        config = await self.rpc.request("dns/cache/config/get")
        record_type = dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Value(
            record_type
        )
        local_zone = self.get_local_zone(config, local_zone_name)

        # This is not really ideal, since it is possible to have multiple entries
        # with the same name and type. This will simply update the first one
        for local_data in local_zone.local_data:
            if local_data.name == record_name and local_data.type == record_type:
                if record_data is not None:
                    local_data.data = record_data
                if ttl is not None:
                    local_data.ttl = ttl
                break
        await self.rpc.request("dns/cache/config/update", config)

    async def remove_local_zone_local_data(
        self,
        local_zone_name: str,
        record_name: str,
        record_type: str,
        record_data: str | None = None,
    ):
        config = await self.rpc.request("dns/cache/config/get")
        record_type = dns_cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Value(
            record_type
        )
        local_zone = self.get_local_zone(config, local_zone_name)
        for i, local_data in enumerate(local_zone.local_data):
            if local_data.name == record_name and local_data.type == record_type:
                if record_data is not None and local_data.data != record_data:
                    continue
                del local_zone.local_data[i]
                break
        await self.rpc.request("dns/cache/config/update", config)
