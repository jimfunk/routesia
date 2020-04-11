"""
routesia/dns/authoritative/commands.py - Routesia authoritative DNS commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import String, IPAddress, IPNetwork, UInt16, UInt32, Bool
from routesia.exceptions import CommandError
from routesia.dns.authoritative import authoritative_pb2


class ZoneParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        data = await client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        for zone in config.zone:
            if zone.name.startswith(suggestion):
                completions.append(zone.name)
        return completions


class ConfigShow(CLICommand):
    command = "dns authoritative config show"

    async def call(self, name=None) -> authoritative_pb2.AuthoritativeDNSConfig:
        data = await self.client.request("/dns/authoritative/config/get", None)
        return authoritative_pb2.AuthoritativeDNSConfig.FromString(data)


class ConfigEnable(CLICommand):
    command = "dns authoritative config enable"

    async def call(self, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        config.enabled = True
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigDisable(CLICommand):
    command = "dns authoritative config disable"

    async def call(self, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        config.enabled = False
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigListenAddressAdd(CLICommand):
    command = "dns authoritative config listen-address add"
    parameters = (
        ("address", IPAddress(required=True)),
        ("port", UInt16()),
    )

    async def call(self, address, port=0, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)

        for listen_address in config.listen_address:
            if listen_address.address == address and listen_address.port == port:
                raise CommandError("Listen address already exists")

        listen_address = config.listen_address.add()
        listen_address.address = address
        listen_address.port = port
        await self.client.request("/dns/authoritative/config/update", config)


async def get_listen_address_address_completions(client, suggestion, **kwargs):
    completions = []
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    for listen_address in config.listen_address:
        if "port" in kwargs and listen_address.port != kwargs["port"].upper():
            continue
        completions.append(listen_address.address)
    return completions


async def get_listen_address_port_completions(client, suggestion, **kwargs):
    completions = []
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    for listen_address in config.listen_address:
        if "address" in kwargs and listen_address.address != kwargs["address"].upper():
            continue
        completions.append(str(listen_address.port))
    return completions


class ConfigListenAddressRemove(CLICommand):
    command = "dns authoritative config listen-address remove"
    parameters = (
        (
            "address",
            IPAddress(required=True, completer=get_listen_address_address_completions),
        ),
        ("port", UInt16(completer=get_listen_address_port_completions)),
    )

    async def call(self, address, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        for i, listen_address in enumerate(config.listen_address):
            if listen_address.address == address:
                if "port" in kwargs and listen_address.port != kwargs["port"]:
                    continue
                del config.listen_address[i]
                break
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneAdd(CLICommand):
    command = "dns authoritative config zone add"
    parameters = (
        ("name", String(required=True)),
        ("email", String(required=True)),
        ("ttl", UInt32()),
        ("refresh", UInt32()),
        ("retry", UInt32()),
        ("minimum-ttl", UInt32()),
        ("use-ipam", Bool()),
    )

    async def call(self, name, email, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)

        for zone in config.zone:
            if zone.name == name:
                raise CommandError("Zone %s already exists" % name)

        zone = config.zone.add()
        zone.name = name
        zone.email = email
        self.update_message_from_args(zone, **kwargs)

        await self.client.request("/dns/authoritative/config/update", config)


class ZoneCLICommand(CLICommand):
    def get_zone(self, config, name):
        for zone in config.zone:
            if zone.name == name:
                return zone
        raise CommandError("Zone %s does not exist" % name)


class ConfigZoneUpdate(ZoneCLICommand):
    command = "dns authoritative config zone update"
    parameters = (
        ("name", ZoneParameter(required=True)),
        ("email", String()),
        ("ttl", UInt32()),
        ("refresh", UInt32()),
        ("retry", UInt32()),
        ("minimum-ttl", UInt32()),
        ("use-ipam", Bool()),
    )

    async def call(self, name, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)

        zone = self.get_zone(config, name)
        self.update_message_from_args(zone, **kwargs)

        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneRemove(CLICommand):
    command = "dns authoritative config zone remove"
    parameters = (("name", ZoneParameter(required=True)),)

    async def call(self, name, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)

        for i, zone in enumerate(config.zone):
            if zone.name == name:
                del config.zone[i]
                break

        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneIPAMNetworkAdd(ZoneCLICommand):
    command = "dns authoritative config zone ipam-network add"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("network", IPNetwork(required=True)),
    )

    async def call(self, zone, network, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        zone = self.get_zone(config, zone)
        for ipam_network in zone.ipam_network:
            if ipam_network == network:
                raise CommandError(
                    "IPAM network %s already exists in zone %s" % (network, zone.name)
                )
        zone.ipam_network.append(network)
        await self.client.request("/dns/authoritative/config/update", config)


async def get_ipam_network_completions(client, suggestion, **kwargs):
    completions = []
    if "zone" not in kwargs:
        return completions
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for ipam_network in zone.ipam_network:
        completions.append(ipam_network)
    return completions


class ConfigZoneIPAMNetworkRemove(ZoneCLICommand):
    command = "dns authoritative config zone ipam-network remove"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("network", IPNetwork(required=True, completer=get_ipam_network_completions)),
    )

    async def call(self, zone, network, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        zone = self.get_zone(config, zone)
        for i, ipam_network in enumerate(zone.ipam_network):
            if ipam_network == network:
                del zone.ipam_network[i]
                break
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneNotifyAdd(ZoneCLICommand):
    command = "dns authoritative config zone notify add"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("address", IPAddress(required=True)),
    )

    async def call(self, zone, address, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        zone = self.get_zone(config, zone)
        for notify in zone.notify:
            if notify == address:
                raise CommandError(
                    "Notify address %s already exists in zone %s" % (address, zone.name)
                )
        zone.notify.append(address)
        await self.client.request("/dns/authoritative/config/update", config)


async def get_notify_completions(client, suggestion, **kwargs):
    completions = []
    if "zone" not in kwargs:
        return completions
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for notify in zone.notify:
        completions.append(notify)
    return completions


class ConfigZoneNotifyRemove(ZoneCLICommand):
    command = "dns authoritative config zone notify remove"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("address", IPAddress(required=True, completer=get_notify_completions)),
    )

    async def call(self, zone, address, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        zone = self.get_zone(config, zone)
        for i, notify in enumerate(zone.notify):
            if notify == address:
                del zone.notify[i]
                break
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneAllowTransferAdd(ZoneCLICommand):
    command = "dns authoritative config zone allow-transfer add"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("address", IPAddress(required=True)),
    )

    async def call(self, zone, address, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        zone = self.get_zone(config, zone)
        for allow_transfer in zone.allow_transfer:
            if allow_transfer == address:
                raise CommandError(
                    "Transfer address %s already exists in zone %s"
                    % (address, zone.name)
                )
        zone.allow_transfer.append(address)
        await self.client.request("/dns/authoritative/config/update", config)


async def get_allow_transfer_completions(client, suggestion, **kwargs):
    completions = []
    if "zone" not in kwargs:
        return completions
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for allow_transfer in zone.allow_transfer:
        completions.append(allow_transfer)
    return completions


class ConfigZoneAllowTransferRemove(ZoneCLICommand):
    command = "dns authoritative config zone allow-transfer remove"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("address", IPAddress(required=True, completer=get_allow_transfer_completions)),
    )

    async def call(self, zone, address, **kwargs):
        data = await self.client.request("/dns/authoritative/config/get", None)
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
        zone = self.get_zone(config, zone)
        for i, allow_transfer in enumerate(zone.allow_transfer):
            if allow_transfer == address:
                del zone.allow_transfer[i]
                break
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneRecordAdd(ZoneCLICommand):
    command = "dns authoritative config zone record add"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("name", String(required=True)),
        ("type", String(required=True)),
        ("data", String(required=True)),
        ("ttl", UInt32()),
    )

    async def call(self, zone, name, type, data, **kwargs):
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(
            await self.client.request("/dns/authoritative/config/get", None)
        )
        zone = self.get_zone(config, zone)
        type = type.upper()
        for record in zone.record:
            if record.name == name and record.type == type and record.data == data:
                raise CommandError(
                    "Record %s %s %s already exists in zone %s"
                    % (name, type, data, zone.name)
                )
        record = zone.record.add()
        record.name = name
        record.type = type
        record.data = data
        self.update_message_from_args(record, **kwargs)
        await self.client.request("/dns/authoritative/config/update", config)


async def get_record_name_completions(client, suggestion, **kwargs):
    completions = []
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    if "zone" not in kwargs:
        return completions
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for record in zone.record:
        if "type" in kwargs and record.type != kwargs["type"].upper():
            continue
        if "data" in kwargs and record.data != kwargs["data"]:
            continue
        completions.append(record.name)
    return completions


async def get_record_type_completions(client, suggestion, **kwargs):
    completions = []
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    if "zone" not in kwargs:
        return completions
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for record in zone.record:
        if "name" in kwargs and record.name != kwargs["name"]:
            continue
        if "data" in kwargs and record.data != kwargs["data"]:
            continue
        completions.append(record.type)
    return completions


async def get_record_data_completions(client, suggestion, **kwargs):
    completions = []
    data = await client.request("/dns/authoritative/config/get", None)
    config = authoritative_pb2.AuthoritativeDNSConfig.FromString(data)
    if "zone" not in kwargs:
        return completions
    for zone in config.zone:
        if zone.name == kwargs["zone"]:
            break
    else:
        return completions
    for record in zone.record:
        if "name" in kwargs and record.name != kwargs["name"]:
            continue
        if "type" in kwargs and record.type != kwargs["type"].upper():
            continue
        completions.append(record.data)
    return completions


class ConfigZoneRecordUpdate(ZoneCLICommand):
    # This is not really ideal, since it is possible to have multiple entries
    # with the same name and type. This will simply update the first one
    command = "dns authoritative config zone record update"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("name", String(required=True, completer=get_record_name_completions)),
        ("type", String(required=True, completer=get_record_type_completions)),
        ("data", String(required=True)),
        ("ttl", UInt32()),
    )

    async def call(self, zone, name, type, data, **kwargs):
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(
            await self.client.request("/dns/authoritative/config/get", None)
        )
        zone = self.get_zone(config, zone)
        for i, record in enumerate(zone.record):
            if record.name == name and record.type == type:
                record.data = data
                self.update_message_from_args(record, **kwargs)
                break
        await self.client.request("/dns/authoritative/config/update", config)


class ConfigZoneRecordRemove(ZoneCLICommand):
    command = "dns authoritative config zone record remove"
    parameters = (
        ("zone", ZoneParameter(required=True)),
        ("name", String(required=True, completer=get_record_name_completions)),
        ("type", String(required=True, completer=get_record_type_completions)),
        ("data", String(completer=get_record_data_completions)),
    )

    async def call(self, zone, name, type, **kwargs):
        config = authoritative_pb2.AuthoritativeDNSConfig.FromString(
            await self.client.request("/dns/authoritative/config/get", None)
        )
        zone = self.get_zone(config, zone)
        for i, record in enumerate(zone.record):
            if record.name == name and record.type == type:
                if "data" in kwargs and record.data != kwargs["data"]:
                    continue
                del zone.record[i]
                break
        await self.client.request("/dns/authoritative/config/update", config)


class AuthoritativeDNSCommandSet(CLICommandSet):
    commands = (
        ConfigShow,
        ConfigEnable,
        ConfigDisable,
        ConfigListenAddressAdd,
        ConfigListenAddressRemove,
        ConfigZoneAdd,
        ConfigZoneUpdate,
        ConfigZoneRemove,
        ConfigZoneIPAMNetworkAdd,
        ConfigZoneIPAMNetworkRemove,
        ConfigZoneNotifyAdd,
        ConfigZoneNotifyRemove,
        ConfigZoneAllowTransferAdd,
        ConfigZoneAllowTransferRemove,
        ConfigZoneRecordAdd,
        ConfigZoneRecordUpdate,
        ConfigZoneRecordRemove,
    )
