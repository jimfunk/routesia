"""
routesia/dns/cache/commands.py - Routesia DNS cache commands
"""
from routesia.cli.command import CLICommand, CLICommandSet
from routesia.cli.parameters import (
    String,
    IPAddress,
    IPNetwork,
    UInt16,
    UInt32,
    Bool,
    ProtobufEnum,
)
from routesia.exceptions import CommandError
from routesia.schema.v1 import cache_pb2


class ConfigShow(CLICommand):
    command = "dns cache config show"

    async def call(self, name=None) -> cache_pb2.DNSCacheConfig:
        return cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )


class ConfigUpdate(CLICommand):
    command = "dns cache config update"
    parameters = (
        ("enabled", Bool()),
        ("tls-upstream", Bool()),
        ("ttl", UInt32()),
    )

    async def call(self, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        self.update_message_from_args(config, **kwargs)
        await self.client.request("/dns/cache/config/update", config)


class ConfigListenAddressAdd(CLICommand):
    command = "dns cache config listen-address add"
    parameters = (
        ("address", IPAddress(required=True)),
        ("port", UInt16()),
    )

    async def call(self, address, port=0, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for listen_address in config.listen_address:
            if listen_address.address == address and listen_address.port == port:
                raise CommandError("Listen address already exists")

        listen_address = config.listen_address.add()
        listen_address.address = address
        listen_address.port = port
        await self.client.request("/dns/cache/config/update", config)


async def get_listen_address_address_completions(client, suggestion, **kwargs):
    completions = []
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for listen_address in config.listen_address:
        if "port" in kwargs and listen_address.port != kwargs["port"].upper():
            continue
        completions.append(listen_address.address)
    return completions


async def get_listen_address_port_completions(client, suggestion, **kwargs):
    completions = []
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for listen_address in config.listen_address:
        if "address" in kwargs and listen_address.address != kwargs["address"].upper():
            continue
        completions.append(str(listen_address.port))
    return completions


class ConfigListenAddressRemove(CLICommand):
    command = "dns cache config listen-address remove"
    parameters = (
        (
            "address",
            IPAddress(required=True, completer=get_listen_address_address_completions),
        ),
        ("port", UInt16(completer=get_listen_address_port_completions)),
    )

    async def call(self, address, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        for i, listen_address in enumerate(config.listen_address):
            if listen_address.address == address:
                if "port" in kwargs and listen_address.port != kwargs["port"]:
                    continue
                del config.listen_address[i]
                break
        await self.client.request("/dns/cache/config/update", config)


class ConfigAccessControlRuleAdd(CLICommand):
    command = "dns cache config access-control-rule add"
    parameters = (
        ("priority", UInt32(required=True)),
        ("network", IPNetwork(required=True)),
        (
            "action",
            ProtobufEnum(
                cache_pb2.DNSCacheAccessControlRule.DNSCacheAccessControlRuleAction,
                required=True,
            ),
        ),
    )

    async def call(self, priority, network, action, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for access_control_rule in config.access_control_rule:
            if (
                access_control_rule.priority == priority
                and access_control_rule.network == network
                and access_control_rule.action == action
            ):
                raise CommandError(
                    "Access control rule %s %s %s already exists"
                    % (priority, network, action)
                )

        access_control_rule = config.access_control_rule.add()
        access_control_rule.priority = priority
        access_control_rule.network = network
        access_control_rule.action = action

        await self.client.request("/dns/cache/config/update", config)


class ConfigAccessControlRuleRemove(CLICommand):
    command = "dns cache config access-control-rule remove"
    parameters = (
        ("priority", UInt32(required=True)),
        ("network", IPNetwork(required=True)),
        (
            "action",
            ProtobufEnum(
                cache_pb2.DNSCacheAccessControlRule.DNSCacheAccessControlRuleAction,
                required=True,
            ),
        ),
    )

    async def call(self, priority, network, action, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for i, access_control_rule in enumerate(config.access_control_rule):
            if (
                access_control_rule.priority == priority
                and access_control_rule.network == network
                and access_control_rule.action == action
            ):
                del config.access_control_rule[i]
                break

        await self.client.request("/dns/cache/config/update", config)


class ConfigForwardZoneAdd(CLICommand):
    command = "dns cache config forward-zone add"
    parameters = (
        ("name", String(required=True)),
        ("forward-tls", Bool()),
    )

    async def call(self, name, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for forward_zone in config.forward_zone:
            if forward_zone.name == name:
                raise CommandError("Forward zone %s already exists" % name)

        forward_zone = config.forward_zone.add()
        forward_zone.name = name
        self.update_message_from_args(forward_zone, **kwargs)

        await self.client.request("/dns/cache/config/update", config)


class ForwardZoneCLICommand(CLICommand):
    def get_forward_zone(self, config, name):
        for forward_zone in config.forward_zone:
            if forward_zone.name == name:
                return forward_zone
        raise CommandError("Forward zone %s does not exist" % name)


class ForwardZoneParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        config = cache_pb2.DNSCacheConfig.FromString(
            await client.request("/dns/cache/config/get", None)
        )
        for forward_zone in config.forward_zone:
            if forward_zone.name.startswith(suggestion):
                completions.append(forward_zone.name)
        return completions


class ConfigForwardZoneUpdate(ForwardZoneCLICommand):
    command = "dns cache config forward-zone update"
    parameters = (
        ("name", ForwardZoneParameter(required=True)),
        ("forward-tls", Bool()),
    )

    async def call(self, name, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        forward_zone = self.get_forward_zone(config, name)
        self.update_message_from_args(forward_zone, **kwargs)

        await self.client.request("/dns/cache/config/update", config)


class ConfigForwardZoneRemove(CLICommand):
    command = "dns cache config forward-zone remove"
    parameters = (("name", ForwardZoneParameter(required=True)),)

    async def call(self, name, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for i, forward_zone in enumerate(config.forward_zone):
            if forward_zone.name == name:
                del config.forward_zone[i]
                break

        await self.client.request("/dns/cache/config/update", config)


class ConfigForwardZoneForwardForwardAddressAdd(ForwardZoneCLICommand):
    command = "dns cache config forward-zone forward-address add"
    parameters = (
        ("forward-zone", ForwardZoneParameter(required=True)),
        ("forward-address", IPAddress(required=True)),
        ("port", UInt16()),
        ("host", String()),
    )

    async def call(self, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        forward_zone = self.get_forward_zone(config, kwargs["forward-zone"])
        address = kwargs["forward-address"]
        for forward_address in forward_zone.forward_address:
            if forward_address.address == address:
                raise CommandError(
                    "Address %s already exists in forward zone %s"
                    % (address, forward_zone.name)
                )
        forward_address = forward_zone.forward_address.add()
        forward_address.address = address
        self.update_message_from_args(forward_address, **kwargs)
        await self.client.request("/dns/cache/config/update", config)


async def get_forward_zone_address_completions(client, suggestion, **kwargs):
    completions = []
    if "forward-zone" not in kwargs:
        return completions
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for forward_zone in config.forward_zone:
        if forward_zone.name == kwargs["forward-zone"]:
            break
    else:
        return completions
    for forward_address in forward_zone.forward_address:
        completions.append(forward_address.address)
    return completions


class ConfigForwardZoneForwardForwardAddressUpdate(ForwardZoneCLICommand):
    command = "dns cache config forward-zone forward-address update"
    parameters = (
        ("forward-zone", ForwardZoneParameter(required=True)),
        (
            "forward-address",
            IPAddress(required=True, completer=get_forward_zone_address_completions),
        ),
        ("port", UInt16()),
        ("host", String()),
    )

    async def call(self, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        forward_zone = self.get_forward_zone(config, kwargs["forward-zone"])
        address = kwargs["forward-address"]
        for i, forward_address in enumerate(forward_zone.forward_address):
            if forward_address.address == address:
                self.update_message_from_args(forward_address, **kwargs)
                break
        await self.client.request("/dns/cache/config/update", config)


class ConfigForwardZoneForwardForwardAddressRemove(ForwardZoneCLICommand):
    command = "dns cache config forward-zone forward-address remove"
    parameters = (
        ("forward-zone", ForwardZoneParameter(required=True)),
        (
            "forward-address",
            IPAddress(required=True, completer=get_forward_zone_address_completions),
        ),
    )

    async def call(self, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        forward_zone = self.get_forward_zone(config, kwargs["forward-zone"])
        address = kwargs["forward-address"]
        for i, forward_address in enumerate(forward_zone.forward_address):
            if forward_address.address == address:
                del forward_zone.forward_address[i]
                break
        await self.client.request("/dns/cache/config/update", config)


class ConfigLocalZoneAdd(CLICommand):
    command = "dns cache config local-zone add"
    parameters = (
        ("name", String(required=True)),
        ("type", ProtobufEnum(cache_pb2.DNSCacheLocalZone.DNSCacheLocalZoneType)),
        ("ttl", UInt32()),
        ("use-ipam", Bool()),
    )

    async def call(self, name, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for local_zone in config.local_zone:
            if local_zone.name == name:
                raise CommandError("Local zone %s already exists" % name)

        local_zone = config.local_zone.add()
        local_zone.name = name
        self.update_message_from_args(local_zone, **kwargs)

        await self.client.request("/dns/cache/config/update", config)


class LocalZoneCLICommand(CLICommand):
    def get_local_zone(self, config, name):
        for local_zone in config.local_zone:
            if local_zone.name == name:
                return local_zone
        raise CommandError("Local zone %s does not exist" % name)


class LocalZoneParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        completions = []
        config = cache_pb2.DNSCacheConfig.FromString(
            await client.request("/dns/cache/config/get", None)
        )
        for local_zone in config.local_zone:
            if local_zone.name.startswith(suggestion):
                completions.append(local_zone.name)
        return completions


class ConfigLocalZoneUpdate(LocalZoneCLICommand):
    command = "dns cache config local-zone update"
    parameters = (
        ("name", LocalZoneParameter(required=True)),
        ("type", ProtobufEnum(cache_pb2.DNSCacheLocalZone.DNSCacheLocalZoneType)),
        ("ttl", UInt32()),
        ("use-ipam", Bool()),
    )

    async def call(self, name, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        local_zone = self.get_local_zone(config, name)
        self.update_message_from_args(local_zone, **kwargs)

        await self.client.request("/dns/cache/config/update", config)


class ConfigLocalZoneRemove(CLICommand):
    command = "dns cache config local-zone remove"
    parameters = (("name", LocalZoneParameter(required=True)),)

    async def call(self, name, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )

        for i, local_zone in enumerate(config.local_zone):
            if local_zone.name == name:
                del config.local_zone[i]
                break

        await self.client.request("/dns/cache/config/update", config)


class ConfigLocalZoneIPAMNetworkAdd(LocalZoneCLICommand):
    command = "dns cache config local-zone ipam-network add"
    parameters = (
        ("local-zone", LocalZoneParameter(required=True)),
        ("network", IPNetwork(required=True)),
    )

    async def call(self, network, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        local_zone = self.get_local_zone(config, kwargs["local-zone"])
        for ipam_network in local_zone.ipam_network:
            if ipam_network == network:
                raise CommandError(
                    "IPAM network %s already exists in local zone %s"
                    % (network, local_zone.name)
                )
        local_zone.ipam_network.append(network)
        await self.client.request("/dns/cache/config/update", config)


async def get_local_zone_ipam_network_completions(client, suggestion, **kwargs):
    completions = []
    if "local-zone" not in kwargs:
        return completions
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for local_zone in config.local_zone:
        if local_zone.name == kwargs["local-zone"]:
            break
    else:
        return completions
    for forward_address in local_zone.forward_address:
        completions.append(forward_address.address)
    return completions


class ConfigLocalZoneIPAMNetworkRemove(LocalZoneCLICommand):
    command = "dns cache config local-zone ipam-network remove"
    parameters = (
        ("local-zone", ForwardZoneParameter(required=True)),
        (
            "network",
            IPNetwork(required=True, completer=get_local_zone_ipam_network_completions),
        ),
    )

    async def call(self, network, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        local_zone = self.get_local_zone(config, kwargs["local-zone"])
        for i, ipam_network in enumerate(local_zone.ipam_network):
            if ipam_network == network:
                del local_zone.ipam_network[i]
                break
        await self.client.request("/dns/cache/config/update", config)


class ConfigLocalZoneLocalDataAdd(LocalZoneCLICommand):
    command = "dns cache config local-zone local-data add"
    parameters = (
        ("local-zone", LocalZoneParameter(required=True)),
        ("name", String(required=True)),
        (
            "type",
            ProtobufEnum(
                cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType, required=True
            ),
        ),
        ("data", String(required=True)),
        ("ttl", UInt32()),
    )

    async def call(self, name, type, data, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        local_zone = self.get_local_zone(config, kwargs["local-zone"])
        for local_data in local_zone.local_data:
            if (
                local_data.name == name
                and local_data.type == type
                and local_data.data == data
            ):
                raise CommandError(
                    "Local data %s %s %s already exists in local zone %s"
                    % (
                        name,
                        cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Name(type),
                        data,
                        local_zone.name,
                    )
                )
        local_data = local_zone.local_data.add()
        local_data.name = name
        local_data.type = type
        local_data.data = data
        self.update_message_from_args(local_data, **kwargs)
        await self.client.request("/dns/cache/config/update", config)


async def get_local_data_name_completions(client, suggestion, **kwargs):
    completions = []
    if "local-zone" not in kwargs:
        return completions
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for local_zone in config.local_zone:
        if local_zone.name == kwargs["local-zone"]:
            break
    else:
        return completions
    for local_data in local_zone.local_data:
        if "type" in kwargs and local_data.type != kwargs["type"]:
            continue
        if "data" in kwargs and local_data.data != kwargs["data"]:
            continue
        completions.append(local_data.name)
    return completions


async def get_local_data_type_completions(client, suggestion, **kwargs):
    completions = []
    if "local-zone" not in kwargs:
        return completions
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for local_zone in config.local_zone:
        if local_zone.name == kwargs["local-zone"]:
            break
    else:
        return completions
    for local_data in local_zone.local_data:
        if "name" in kwargs and local_data.name != kwargs["name"]:
            continue
        if "data" in kwargs and local_data.data != kwargs["data"]:
            continue
        completions.append(
            cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType.Name(local_data.type)
        )
    return completions


async def get_local_data_data_completions(client, suggestion, **kwargs):
    completions = []
    if "local-zone" not in kwargs:
        return completions
    config = cache_pb2.DNSCacheConfig.FromString(
        await client.request("/dns/cache/config/get", None)
    )
    for local_zone in config.local_zone:
        if local_zone.name == kwargs["local-zone"]:
            break
    else:
        return completions
    for local_data in local_zone.local_data:
        if "name" in kwargs and local_data.name != kwargs["name"]:
            continue
        if "type" in kwargs and local_data.type != kwargs["type"]:
            continue
        completions.append(local_data.data)
    return completions


class ConfigLocalZoneLocalDataUpdate(LocalZoneCLICommand):
    # This is not really ideal, since it is possible to have multiple entries
    # with the same name and type. This will simply update the first one
    command = "dns cache config local-zone local-data update"
    parameters = (
        ("local-zone", LocalZoneParameter(required=True)),
        ("name", String(required=True, completer=get_local_data_name_completions)),
        (
            "type",
            ProtobufEnum(
                cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType,
                required=True,
                completer=get_local_data_type_completions,
            ),
        ),
        ("data", String()),
        ("ttl", UInt32()),
    )

    async def call(self, name, type, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        local_zone = self.get_local_zone(config, kwargs["local-zone"])
        for i, local_data in enumerate(local_zone.local_data):
            if local_data.name == name and local_data.type == type:
                self.update_message_from_args(local_data, **kwargs)
                break
        await self.client.request("/dns/cache/config/update", config)


class ConfigLocalZoneLocalDataRemove(LocalZoneCLICommand):
    command = "dns cache config local-zone local-data remove"
    parameters = (
        ("local-zone", LocalZoneParameter(required=True)),
        ("name", String(required=True, completer=get_local_data_name_completions)),
        (
            "type",
            ProtobufEnum(
                cache_pb2.DNSCacheLocalData.DNSCacheLocalDataType,
                required=True,
                completer=get_local_data_type_completions,
            ),
        ),
        ("data", String(completer=get_local_data_data_completions)),
    )

    async def call(self, name, type, **kwargs):
        config = cache_pb2.DNSCacheConfig.FromString(
            await self.client.request("/dns/cache/config/get", None)
        )
        local_zone = self.get_local_zone(config, kwargs["local-zone"])
        for i, local_data in enumerate(local_zone.local_data):
            if local_data.name == name and local_data.type == type:
                if "data" in kwargs and local_data.data != kwargs["data"]:
                    continue
                del local_zone.local_data[i]
                break
        await self.client.request("/dns/cache/config/update", config)


class CacheDNSCommandSet(CLICommandSet):
    commands = (
        ConfigShow,
        ConfigUpdate,
        ConfigListenAddressAdd,
        ConfigListenAddressRemove,
        ConfigAccessControlRuleAdd,
        ConfigAccessControlRuleRemove,
        ConfigForwardZoneAdd,
        ConfigForwardZoneUpdate,
        ConfigForwardZoneRemove,
        ConfigForwardZoneForwardForwardAddressAdd,
        ConfigForwardZoneForwardForwardAddressUpdate,
        ConfigForwardZoneForwardForwardAddressRemove,
        ConfigLocalZoneAdd,
        ConfigLocalZoneUpdate,
        ConfigLocalZoneRemove,
        ConfigLocalZoneIPAMNetworkAdd,
        ConfigLocalZoneIPAMNetworkRemove,
        ConfigLocalZoneLocalDataAdd,
        ConfigLocalZoneLocalDataUpdate,
        ConfigLocalZoneLocalDataRemove,
    )
