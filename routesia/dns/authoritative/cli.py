"""
routesia/dns/authoritative/cli.py - Routesia authoritative DNS commands
"""

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from routesia.cli import CLI, InvalidArgument
from routesia.cli.types import UInt16, UInt32
from routesia.rpcclient import RPCClient
from routesia.service import Provider


class DNSAuthoritativeCLI(Provider):
    def __init__(self, cli: CLI, rpc: RPCClient):
        super().__init__()
        self.cli = cli.get_namespace_cli("dns-authoritative")
        self.rpc = rpc

        self.cli.add_argument_completer("listen-address", self.complete_listen_address)
        self.cli.add_argument_completer("listen-port", self.complete_listen_port)
        self.cli.add_argument_completer("zone", self.complete_zone)
        self.cli.add_argument_completer(
            "zone-ipam-network", self.complete_zone_ipam_network
        )
        self.cli.add_argument_completer(
            "zone-notify-address", self.complete_zone_notify_address
        )
        self.cli.add_argument_completer(
            "zone-allow-transfer-network", self.complete_zone_allow_transfer_network
        )
        self.cli.add_argument_completer(
            "zone-record-name", self.complete_zone_record_name
        )
        self.cli.add_argument_completer(
            "zone-record-type", self.complete_zone_record_type
        )
        self.cli.add_argument_completer(
            "zone-record-data", self.complete_zone_record_data
        )

        self.cli.add_command("dns authoritative config show", self.show_config)
        self.cli.add_command(
            "dns authoritative config set @enabled @servers", self.set_config
        )
        self.cli.add_command(
            "dns authoritative config listen-address add :listen-address! @listen-port!",
            self.add_listen_address,
        )
        self.cli.add_command(
            "dns authoritative config listen-address remove :listen-address @listen-port",
            self.remove_listen_address,
        )
        self.cli.add_command(
            "dns authoritative config zone add :name :email @ttl @refresh @retry @minimum-ttl @use-ipam",
            self.add_zone,
        )
        self.cli.add_command(
            "dns authoritative config zone update :zone-name @email @ttl @refresh @retry @minimum-ttl @use-ipam",
            self.update_zone,
        )
        self.cli.add_command(
            "dns authoritative config zone remove :zone-name", self.remove_zone
        )
        self.cli.add_command(
            "dns authoritative config zone ipam-network add :zone-name :network",
            self.add_zone_ipam_network,
        )
        self.cli.add_command(
            "dns authoritative config zone ipam-network remove :zone-name :zone-ipam-network",
            self.remove_zone_ipam_network,
        )
        self.cli.add_command(
            "dns authoritative config zone notify add :zone-name :address",
            self.add_zone_notify,
        )
        self.cli.add_command(
            "dns authoritative config zone notify remove :zone-name :zone-notify-address",
            self.remove_zone_notify,
        )
        self.cli.add_command(
            "dns authoritative config zone allow-transfer add :zone-name :network",
            self.add_zone_allow_transfer,
        )
        self.cli.add_command(
            "dns authoritative config zone allow-transfer remove :zone-name :zone-allow-transfer-network",
            self.remove_zone_allow_transfer,
        )
        self.cli.add_command(
            "dns authoritative config zone record add :zone-name :name :type :data @ttl",
            self.add_zone_record,
        )
        self.cli.add_command(
            "dns authoritative config zone record update :zone-name :zone-record-name :zone-record-type @zone-record-data @ttl",
            self.update_zone_record,
        )
        self.cli.add_command(
            "dns authoritative config zone record delete :zone-name :zone-record-name :zone-record-type @zone-record-data",
            self.delete_zone_record,
        )

    async def complete_listen_address(self, port: int | None = None):
        completions = []
        config = await self.rpc.request("dns/authoritative/config/get")
        for listen_address in config.listen_address:
            if port is not None and listen_address.port != port:
                continue
            completions.append(listen_address.address)
        return completions

    async def complete_listen_port(
        self, address: IPv4Address | IPv6Address | None = None
    ):
        completions = []
        config = await self.rpc.request("dns/authoritative/config/get")
        if address is not None:
            address = str(address)
        for listen_address in config.listen_address:
            if address is not None and listen_address.address != address:
                continue
            completions.append(str(listen_address.port))
        return completions

    async def complete_zone(self):
        completions = []
        config = await self.rpc.request("dns/authoritative/config/get")

        for zone in config.zone:
            completions.append(zone.name)
        return completions

    async def complete_zone_ipam_network(self, zone_name: str | None = None):
        completions = []
        if zone_name is None:
            return completions
        config = await self.rpc.request("dns/authoritative/config/get")
        try:
            zone = self.get_zone(config, zone_name)
        except InvalidArgument:
            pass
        else:
            for ipam_network in zone.ipam_network:
                completions.append(ipam_network)
        return completions

    async def complete_zone_notify_address(self, zone_name: str | None = None):
        completions = []
        if zone_name is None:
            return completions
        config = await self.rpc.request("dns/authoritative/config/get")
        try:
            zone = self.get_zone(config, zone_name)
        except InvalidArgument:
            pass
        else:
            for notify in zone.notify:
                completions.append(notify)
        return completions

    async def complete_zone_allow_transfer_network(self, zone_name: str | None = None):
        completions = []
        if zone_name is None:
            return completions
        config = await self.rpc.request("dns/authoritative/config/get")
        try:
            zone = self.get_zone(config, zone_name)
        except InvalidArgument:
            pass
        else:
            for allow_transfer in zone.allow_transfer:
                completions.append(allow_transfer)
        return completions

    async def complete_zone_record_name(
        self,
        zone_name: str | None = None,
        type: str | None = None,
        data: str | None = None,
    ):
        completions = set()
        if zone_name is None:
            return list(completions)
        config = await self.rpc.request("dns/authoritative/config/get")
        try:
            zone = self.get_zone(config, zone_name)
        except InvalidArgument:
            pass
        else:
            if type is not None:
                type = type.upper()
            for record in zone.record:
                if type and record.type != type:
                    continue
                if data and record.data != data:
                    continue
                completions.add(record.name)
        return list(completions)

    async def complete_zone_record_type(
        self,
        zone_name: str | None = None,
        name: str | None = None,
        data: str | None = None,
    ):
        completions = set()
        if zone_name is None:
            return list(completions)
        config = await self.rpc.request("dns/authoritative/config/get")
        try:
            zone = self.get_zone(config, zone_name)
        except InvalidArgument:
            pass
        else:
            for record in zone.record:
                if name and record.name != name:
                    continue
                if data and record.data != data:
                    continue
                completions.add(record.type)
        return list(completions)

    async def complete_zone_record_data(
        self,
        zone_name: str | None = None,
        name: str | None = None,
        type: str | None = None,
    ):
        completions = []
        if zone_name is None:
            return completions
        config = await self.rpc.request("dns/authoritative/config/get")
        try:
            zone = self.get_zone(config, zone_name)
        except InvalidArgument:
            pass
        else:
            if type is not None:
                type = args["type"].upper()
            for record in zone.record:
                if name and record.name != name:
                    continue
                if type and record.type != type:
                    continue
                completions.append(record.data)
        return completions

    async def show_config(self):
        return await self.rpc.request("dns/authoritative/config/get")

    async def set_config(self, enabled: bool = None, servers: UInt32 = None):
        config = await self.rpc.request("dns/authoritative/config/get")
        if enabled is not None:
            config.enabled = enabled
        if servers is not None:
            config.servers = servers
        await self.rpc.request("dns/authoritative/config/update", config)

    async def add_listen_address(self, address: IPv4Address, port: UInt16 = 0):
        config = await self.rpc.request("dns/authoritative/config/get")

        for listen_address in config.listen_address:
            if listen_address.address == address and listen_address.port == port:
                raise InvalidArgument("Listen address already exists")

        listen_address = config.listen_address.add()
        listen_address.address = str(address)
        listen_address.port = port
        await self.rpc.request("dns/authoritative/config/update", config)

    async def remove_listen_address(
        self,
        listen_address: IPv4Address | IPv6Address,
        listen_port: UInt16 = 0,
    ):
        address = str(listen_address)
        config = await self.rpc.request("dns/authoritative/config/get")
        for i, listen_address in enumerate(config.listen_address):
            if listen_address.address == address:
                if listen_address.port != listen_port:
                    continue
                del config.listen_address[i]
                break
        await self.rpc.request("dns/authoritative/config/update", config)

    async def add_zone(
        self,
        name: str,
        email: str,
        ttl: UInt32 = None,
        refresh: UInt32 = None,
        retry: UInt32 = None,
        minimum_ttl: UInt32 = None,
        use_ipam: bool = None,
    ):
        config = await self.rpc.request("dns/authoritative/config/get")

        for zone in config.zone:
            if zone.name == name:
                raise InvalidArgument("Zone %s already exists" % name)

        zone = config.zone.add()
        zone.name = name
        zone.email = email
        if ttl is not None:
            zone.ttl = ttl
        if refresh is not None:
            zone.refresh = refresh
        if retry is not None:
            zone.retry = retry
        if minimum_ttl is not None:
            zone.minimum_ttl = minimum_ttl
        if use_ipam is not None:
            zone.use_ipam = use_ipam

        await self.rpc.request("dns/authoritative/config/update", config)

    def get_zone(self, config, name: str):
        for zone in config.zone:
            if zone.name == name:
                return zone
        raise InvalidArgument("Zone %s does not exist" % name)

    async def update_zone(
        self,
        zone_name: str,
        email: str | None = None,
        ttl: UInt32 = None,
        refresh: UInt32 = None,
        retry: UInt32 = None,
        minimum_ttl: UInt32 = None,
        use_ipam: bool = None,
    ):
        config = await self.rpc.request("dns/authoritative/config/get")

        zone = self.get_zone(config, zone_name)
        if email is not None:
            zone.email = email
        if ttl is not None:
            zone.ttl = ttl
        if refresh is not None:
            zone.refresh = refresh
        if retry is not None:
            zone.retry = retry
        if minimum_ttl is not None:
            zone.minimum_ttl = minimum_ttl
        if use_ipam is not None:
            zone.use_ipam = use_ipam

        await self.rpc.request("dns/authoritative/config/update", config)

    async def remove_zone(self, zone_name: str):
        config = await self.rpc.request("dns/authoritative/config/get")

        for i, zone in enumerate(config.zone):
            if zone.name == zone_name:
                del config.zone[i]
                break

        await self.rpc.request("dns/authoritative/config/update", config)

    async def add_zone_ipam_network(
        self, zone_name: str, network: IPv4Network | IPv6Network
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        network = str(network)
        for ipam_network in zone.ipam_network:
            if ipam_network == network:
                raise InvalidArgument(
                    "IPAM network %s already exists in zone %s" % (network, zone.name)
                )
        zone.ipam_network.append(network)
        await self.rpc.request("dns/authoritative/config/update", config)

    async def remove_zone_ipam_network(
        self, zone_name: str, zone_ipam_network: IPv4Network | IPv6Network
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        network = str(zone_ipam_network)
        for i, ipam_network in enumerate(zone.ipam_network):
            if ipam_network == network:
                del zone.ipam_network[i]
                break
        await self.rpc.request("dns/authoritative/config/update", config)

    async def add_zone_notify(self, zone_name: str, address: IPv4Address | IPv6Address):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        address = str(address)
        for notify in zone.notify:
            if notify == address:
                raise InvalidArgument(
                    "Notify address %s already exists in zone %s" % (address, zone.name)
                )
        zone.notify.append(address)
        await self.rpc.request("dns/authoritative/config/update", config)

    async def remove_zone_notify(
        self, zone_name: str, zone_notify_address: IPv4Address | IPv6Address
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        address = str(zone_notify_address)
        for i, notify in enumerate(zone.notify):
            if notify == address:
                del zone.notify[i]
                break
        await self.rpc.request("dns/authoritative/config/update", config)

    async def add_zone_allow_transfer(
        self, zone_name: str, network: IPv4Network | IPv6Network
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        network = str(network)
        for allow_transfer in zone.allow_transfer:
            if allow_transfer == network:
                raise InvalidArgument(
                    "Transfer address %s already exists in zone %s"
                    % (network, zone.name)
                )
        zone.allow_transfer.append(network)
        await self.rpc.request("dns/authoritative/config/update", config)

    async def remove_zone_allow_transfer(
        self, zone_name: str, zone_allow_transfer_network: IPv4Network | IPv6Network
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        network = str(zone_allow_transfer_network)
        for i, allow_transfer in enumerate(zone.allow_transfer):
            if allow_transfer == network:
                del zone.allow_transfer[i]
                break
        await self.rpc.request("dns/authoritative/config/update", config)

    async def add_zone_record(
        self, zone_name: str, name: str, type: str, data: str, ttl: UInt32 = None
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        type = type.upper()
        for record in zone.record:
            if record.name == name and record.type == type and record.data == data:
                raise InvalidArgument(
                    "Record %s %s %s already exists in zone %s"
                    % (name, type, data, zone.name)
                )
        record = zone.record.add()
        record.name = name
        record.type = type
        record.data = data
        if ttl is not None:
            record.ttl = ttl
        await self.rpc.request("dns/authoritative/config/update", config)

    async def update_zone_record(
        self,
        zone_name: str,
        zone_record_name: str,
        zone_record_type: str,
        zone_record_data: str = None,
        ttl: UInt32 = None,
    ):
        # This is not really ideal, since it is possible to have multiple entries
        # with the same name and type. This will simply update the first one
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        updated = False
        if ttl is not None:
            # Try updating just the TTL if data is not given or matches an
            # existing record
            for record in zone.record:
                if (
                    record.name == zone_record_name
                    and record.type == zone_record_type
                    and record.data
                    and (zone_record_data is None or record.data == zone_record_data)
                ):
                    record.ttl = ttl
                    updated = True
                    break
        if not updated:
            # Update data or data and ttl
            for record in zone.record:
                if record.name == zone_record_name and record.type == zone_record_type:
                    record.data = zone_record_data
                    if ttl is not None:
                        record.ttl = ttl
                    break
        await self.rpc.request("dns/authoritative/config/update", config)

    async def delete_zone_record(
        self,
        zone_name: str,
        zone_record_name: str,
        zone_record_type: str,
        zone_record_data: str = None,
    ):
        config = await self.rpc.request("dns/authoritative/config/get")
        zone = self.get_zone(config, zone_name)
        for i, record in enumerate(zone.record):
            if (
                record.name == zone_record_name
                and record.type == zone_record_type
                and (zone_record_data is None or record.data == zone_record_data)
            ):
                del zone.record[i]
                break
        await self.rpc.request("dns/authoritative/config/update", config)
