"""
routesia/dhcp/server/commands/v4/subnet.py - Routesia DHCPv4 server subnet commands
"""
import ipaddress

from routesia.cli.command import CLICommand
from routesia.cli.parameters import Bool, IPAddress, HardwareAddress, String, UInt32
from routesia.exceptions import CommandError
from routesia.dhcp.server import dhcpserver_pb2


class V4ConfigSubnetList(CLICommand):
    command = "dhcp server v4 config subnet list"

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        return "\n".join([str(d) for d in config.subnet])


class V4ConfigSubnetAdd(CLICommand):
    command = "dhcp server v4 config subnet add"
    parameters = (
        ("address", String(required=True)),
        ("use-ipam", Bool()),
        ("next-server", String()),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        self.update_message_from_args(subnet, **kwargs)
        await self.client.request("/dhcp/server/v4/config/subnet/add", subnet)


class SubnetParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        for subnet in config.subnet:
            if subnet.address.startswith(suggestion):
                completions.append(subnet.address)
        return completions


class V4ConfigSubnetUpdate(CLICommand):
    command = "dhcp server v4 config subnet update"
    parameters = (
        ("address", SubnetParameter(required=True)),
        ("use-ipam", Bool()),
        ("next-server", String()),
    )

    async def call(self, address, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        subnet = None
        for sn in config.subnet:
            if sn.address == address:
                subnet = sn
                break
        if not subnet:
            raise CommandError("No such subnet: %s" % address)
        self.update_message_from_args(subnet, **kwargs)
        await self.client.request("/dhcp/server/v4/config/subnet/update", subnet)


class V4ConfigSubnetDelete(CLICommand):
    command = "dhcp server v4 config subnet delete"
    parameters = (("address", SubnetParameter(required=True)),)

    async def call(self, address, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = address
        await self.client.request("/dhcp/server/v4/config/subnet/delete", subnet)


class V4SubnetLeases(CLICommand):
    command = "dhcp server v4 subnet leases"
    parameters = (("address", SubnetParameter(required=True)),)

    async def call(self, address, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = address
        data = await self.client.request("/dhcp/server/v4/subnet/leases", subnet)
        return dhcpserver_pb2.DHCPv4LeaseList.FromString(data)


class Pool(String):
    def __init__(self, min_length=None, max_length=None, regex=None, **kwargs):
        ip_re = r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
        pool_re = "^%s-%s$" % (ip_re, ip_re)
        super().__init__(regex=pool_re, **kwargs)

    def __call__(self, value):
        value = super().__call__(value)
        start, end = value.split("-")
        start = ipaddress.ip_address(start)
        end = ipaddress.ip_address(end)
        if start > end:
            raise ValueError("Start address must be <= end address")
        return value


async def pool_completer(client, suggestion, **kwargs):
    data = await client.request("/dhcp/server/v4/config/get", None)
    config = dhcpserver_pb2.DHCPv4Server.FromString(data)
    completions = []
    subnet_address = kwargs.get("subnet", None)
    subnet = None

    if not subnet_address:
        return []

    for sn in config.subnet:
        if sn.address == subnet_address:
            subnet = sn
            break
    else:
        return []

    for pool in subnet.pool:
        if pool.startswith(suggestion):
            completions.append(pool)
    return completions


class V4ConfigSubnetPoolAdd(CLICommand):
    command = "dhcp server v4 config subnet pool add"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("pool", Pool(required=True)),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        subnet.pool.append(kwargs["pool"])
        await self.client.request("/dhcp/server/v4/config/subnet/pool/add", subnet)


class V4ConfigSubnetPoolDelete(CLICommand):
    command = "dhcp server v4 config subnet pool delete"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("pool", Pool(required=True, completer=pool_completer)),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        subnet.pool.append(kwargs["pool"])
        await self.client.request("/dhcp/server/v4/config/subnet/pool/delete", subnet)


class V4ConfigSubnetOptionList(CLICommand):
    command = "dhcp server v4 config subnet option list"
    parameters = (("subnet", SubnetParameter(required=True)),)

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        subnet = None
        for sn in config.subnet:
            if sn.address == kwargs["subnet"]:
                subnet = sn
                break
        if not subnet:
            raise CommandError("No such subnet: %s" % kwargs["subnet"])

        return "\n".join([str(d) for d in subnet.option])


class V4ConfigSubnetOptionAdd(CLICommand):
    command = "dhcp server v4 config subnet option add"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("name", String()),
        ("code", UInt32()),
        ("data", String(required=True)),
    )

    async def call(self, **kwargs):
        if not ("name" in kwargs or "code" in kwargs):
            raise CommandError("name or code must be specified")

        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        option = subnet.option.add()
        self.update_message_from_args(option, **kwargs)
        await self.client.request("/dhcp/server/v4/config/subnet/option/add", subnet)


class SubnetOptionNameParameter(String):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        subnet_address = kwargs.get("subnet", None)
        subnet = None

        for sn in config.subnet:
            if sn.address == subnet_address:
                subnet = sn
                break
        else:
            return []

        for option in subnet.option:
            if option.name.startswith(suggestion):
                completions.append(option.name)
        return completions


class SubnetOptionCodeParameter(UInt32):
    async def get_completions(self, client, suggestion, **kwargs):
        data = await client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)
        completions = []
        subnet_address = kwargs.get("subnet", None)
        subnet = None

        for sn in config.subnet:
            if sn.address == subnet_address:
                subnet = sn
                break
        else:
            return []

        for option in subnet.option:
            if str(option.code).startswith(suggestion):
                completions.append(str(option.code))
        return completions


class V4ConfigSubnetOptionUpdate(CLICommand):
    command = "dhcp server v4 config subnet option update"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("name", SubnetOptionNameParameter()),
        ("code", SubnetOptionCodeParameter()),
        ("data", String()),
    )

    async def call(self, **kwargs):
        field = None
        if "name" in kwargs:
            field = "name"
        elif "code" in kwargs:
            field = "code"

        if not field:
            raise CommandError("name or code must be specified")

        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        subnet = None
        for sn in config.subnet:
            if sn.address == kwargs["subnet"]:
                subnet = sn
                break
        if not subnet:
            raise CommandError("No such subnet: %s" % kwargs["subnet"])

        option = None
        for opt in subnet.option:
            if getattr(opt, field) == kwargs[field]:
                option = opt
                break
        if not option:
            raise CommandError("No such option with %s of %s" % (field, kwargs[field]))

        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        option = subnet.option.add()
        option.CopyFrom(option)
        self.update_message_from_args(option, **kwargs)
        await self.client.request("/dhcp/server/v4/config/subnet/option/update", subnet)


class V4ConfigSubnetOptionDelete(CLICommand):
    command = "dhcp server v4 config subnet option delete"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("name", SubnetOptionNameParameter()),
        ("code", SubnetOptionCodeParameter()),
    )

    async def call(self, **kwargs):
        field = None
        if "name" in kwargs:
            field = "name"
        elif "code" in kwargs:
            field = "code"

        if not field:
            raise CommandError("name or code must be specified")

        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        option = subnet.option.add()
        setattr(option, field, kwargs[field])
        await self.client.request("/dhcp/server/v4/config/subnet/option/delete", subnet)


class V4ConfigSubnetReservationList(CLICommand):
    command = "dhcp server v4 config subnet reservation list"
    parameters = (("subnet", SubnetParameter(required=True)),)

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        subnet = None
        for sn in config.subnet:
            if sn.address == kwargs["subnet"]:
                subnet = sn
                break
        if not subnet:
            raise CommandError("No such subnet: %s" % kwargs["subnet"])

        return "\n".join([str(d) for d in subnet.reservation])


class V4ConfigSubnetReservationAdd(CLICommand):
    command = "dhcp server v4 config subnet reservation add"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("hardware-address", HardwareAddress(required=True)),
        ("ip-address", IPAddress(required=True)),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        reservation = subnet.reservation.add()
        self.update_message_from_args(reservation, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/subnet/reservation/add", subnet
        )


async def reservation_hardware_address_completer(client, suggestion, **kwargs):
    data = await client.request("/dhcp/server/v4/config/get", None)
    config = dhcpserver_pb2.DHCPv4Server.FromString(data)
    completions = []
    subnet_address = kwargs.get("subnet", None)
    subnet = None

    for sn in config.subnet:
        if sn.address == subnet_address:
            subnet = sn
            break
    else:
        return []

    for reservation in subnet.reservation:
        if reservation.hardware_address.startswith(suggestion):
            completions.append(reservation.hardware_address)
    return completions


class V4ConfigSubnetReservationUpdate(CLICommand):
    command = "dhcp server v4 config subnet reservation update"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        (
            "hardware-address",
            HardwareAddress(
                required=True, completer=reservation_hardware_address_completer
            ),
        ),
        ("ip-address", IPAddress(required=True)),
    )

    async def call(self, **kwargs):
        data = await self.client.request("/dhcp/server/v4/config/get", None)
        config = dhcpserver_pb2.DHCPv4Server.FromString(data)

        subnet = None
        for sn in config.subnet:
            if sn.address == kwargs["subnet"]:
                subnet = sn
                break
        if not subnet:
            raise CommandError("No such subnet: %s" % kwargs["subnet"])

        reservation = None
        for res in subnet.reservation:
            if res.hardware_address == kwargs["hardware-address"]:
                reservation = res
                break
        if not reservation:
            raise CommandError("No such reservation: %s" % kwargs["subnet"])

        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        updated_reservation = subnet.reservation.add()
        updated_reservation.CopyFrom(reservation)
        self.update_message_from_args(updated_reservation, **kwargs)
        await self.client.request(
            "/dhcp/server/v4/config/subnet/reservation/update", subnet
        )


class V4ConfigSubnetReservationDelete(CLICommand):
    command = "dhcp server v4 config subnet reservation delete"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        (
            "hardware-address",
            HardwareAddress(
                required=True, completer=reservation_hardware_address_completer
            ),
        ),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        reservation = subnet.reservation.add()
        reservation.hardware_address = kwargs["hardware-address"]
        await self.client.request(
            "/dhcp/server/v4/config/subnet/reservation/delete", subnet
        )


async def relay_address_completer(client, suggestion, **kwargs):
    data = await client.request("/dhcp/server/v4/config/get", None)
    config = dhcpserver_pb2.DHCPv4Server.FromString(data)
    completions = []
    subnet_address = kwargs.get("subnet", None)
    subnet = None

    if not subnet_address:
        return []

    for sn in config.subnet:
        if sn.address == subnet_address:
            subnet = sn
            break
    else:
        return []

    for relay_address in subnet.relay_address:
        if relay_address.startswith(suggestion):
            completions.append(relay_address)
    return completions


class V4ConfigSubnetRelayAddressAdd(CLICommand):
    command = "dhcp server v4 config subnet relay-address add"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("relay-address", IPAddress(required=True)),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        subnet.relay_address.append(kwargs["relay-address"])
        await self.client.request("/dhcp/server/v4/config/subnet/relay_address/add", subnet)


class V4ConfigSubnetRelayAddressDelete(CLICommand):
    command = "dhcp server v4 config subnet relay-address delete"
    parameters = (
        ("subnet", SubnetParameter(required=True)),
        ("relay-address", IPAddress(required=True, completer=relay_address_completer)),
    )

    async def call(self, **kwargs):
        subnet = dhcpserver_pb2.DHCPv4Subnet()
        subnet.address = kwargs["subnet"]
        subnet.relay_address.append(kwargs["relay-address"])
        await self.client.request("/dhcp/server/v4/config/subnet/relay_address/delete", subnet)
