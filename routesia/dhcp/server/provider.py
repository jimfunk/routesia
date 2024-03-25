"""
routesia/dhcp/provider.py - DHCP support using ISC Kea
"""

from dbus.exceptions import DBusException
import json
import logging
import shutil
import socket
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dhcp.server.config import DHCP4Config
from routesia.rpc import RPCInvalidArgument
from routesia.service import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.rpc import RPC
from routesia.rtnetlink.events import InterfaceAddEvent, InterfaceRemoveEvent
from routesia.schema.v1 import dhcp_server_pb2
from routesia.service import Service
from routesia.systemd import SystemdProvider


DHCP4_CONF = "/etc/kea/kea-dhcp4.conf"
DHCP4_CONTROL_SOCK = "/tmp/kea-dhcp4-ctrl.sock"
DHCP4_LEASE_DB = "/var/lib/kea/dhcp4.leases"

SERVER_CHUNK_SIZE = 65535


logger = logging.getLogger("dhcp-server")


class DHCPServerProvider(Provider):
    def __init__(
        self,
        service: Service,
        config: ConfigProvider,
        ipam: IPAMProvider,
        systemd: SystemdProvider,
        rpc: RPC,
    ):
        self.service = service
        self.config = config
        self.ipam = ipam
        self.systemd = systemd
        self.rpc = rpc

        self.interfaces = set()

        self.config.register_change_handler(self.on_config_change)

        self.service.subscribe_event(InterfaceAddEvent, self.handle_interface_add)
        self.service.subscribe_event(InterfaceRemoveEvent, self.handle_interface_remove)

        self.rpc.register("dhcp/server/v4/subnet/leases", self.rpc_v4_subnet_leases)
        self.rpc.register("dhcp/server/v4/config/get", self.rpc_v4_config_get)
        self.rpc.register("dhcp/server/v4/config/interface/add", self.rpc_v4_config_interface_add)
        self.rpc.register("dhcp/server/v4/config/interface/delete", self.rpc_v4_config_interface_delete)
        self.rpc.register("dhcp/server/v4/config/global_settings/update", self.rpc_v4_config_global_settings_update)
        self.rpc.register("dhcp/server/v4/config/option_definition/add", self.rpc_v4_config_option_definition_add)
        self.rpc.register("dhcp/server/v4/config/option_definition/update", self.rpc_v4_config_option_definition_update)
        self.rpc.register("dhcp/server/v4/config/option_definition/delete", self.rpc_v4_config_option_definition_delete)
        self.rpc.register("dhcp/server/v4/config/option/add", self.rpc_v4_config_option_add)
        self.rpc.register("dhcp/server/v4/config/option/update", self.rpc_v4_config_option_update)
        self.rpc.register("dhcp/server/v4/config/option/delete", self.rpc_v4_config_option_delete)
        self.rpc.register("dhcp/server/v4/config/client_class/add", self.rpc_v4_config_client_class_add)
        self.rpc.register("dhcp/server/v4/config/client_class/update", self.rpc_v4_config_client_class_update)
        self.rpc.register("dhcp/server/v4/config/client_class/delete", self.rpc_v4_config_client_class_delete)
        self.rpc.register("dhcp/server/v4/config/client_class/option_definition/add", self.rpc_v4_config_client_class_option_definition_add)
        self.rpc.register("dhcp/server/v4/config/client_class/option_definition/update", self.rpc_v4_config_client_class_option_definition_update)
        self.rpc.register("dhcp/server/v4/config/client_class/option_definition/delete", self.rpc_v4_config_client_class_option_definition_delete)
        self.rpc.register("dhcp/server/v4/config/client_class/option/add", self.rpc_v4_config_client_class_option_add)
        self.rpc.register("dhcp/server/v4/config/client_class/option/update", self.rpc_v4_config_client_class_option_update)
        self.rpc.register("dhcp/server/v4/config/client_class/option/delete", self.rpc_v4_config_client_class_option_delete)
        self.rpc.register("dhcp/server/v4/config/subnet/add", self.rpc_v4_config_subnet_add)
        self.rpc.register("dhcp/server/v4/config/subnet/update", self.rpc_v4_config_subnet_update)
        self.rpc.register("dhcp/server/v4/config/subnet/delete", self.rpc_v4_config_subnet_delete)
        self.rpc.register("dhcp/server/v4/config/subnet/pool/add", self.rpc_v4_config_subnet_pool_add)
        self.rpc.register("dhcp/server/v4/config/subnet/pool/delete", self.rpc_v4_config_subnet_pool_delete)
        self.rpc.register("dhcp/server/v4/config/subnet/option/add", self.rpc_v4_config_subnet_option_add)
        self.rpc.register("dhcp/server/v4/config/subnet/option/update", self.rpc_v4_config_subnet_option_update)
        self.rpc.register("dhcp/server/v4/config/subnet/option/delete", self.rpc_v4_config_subnet_option_delete)
        self.rpc.register("dhcp/server/v4/config/subnet/reservation/add", self.rpc_v4_config_subnet_reservation_add)
        self.rpc.register("dhcp/server/v4/config/subnet/reservation/update", self.rpc_v4_config_subnet_reservation_update)
        self.rpc.register("dhcp/server/v4/config/subnet/reservation/delete", self.rpc_v4_config_subnet_reservation_delete)
        self.rpc.register("dhcp/server/v4/config/subnet/relay_address/add", self.rpc_v4_config_subnet_relay_address_add)
        self.rpc.register("dhcp/server/v4/config/subnet/relay_address/delete", self.rpc_v4_config_subnet_relay_address_delete)

    def on_config_change(self, config):
        self.apply()

    def is_configured_interface(self, interface):
        "Return True if interface is configured for DHCP"
        for configured_interface in self.config.data.dhcp.server.v4.interface:
            if configured_interface == interface:
                return True
        return False

    async def handle_interface_add(self, interface_event):
        self.interfaces.add(interface_event.ifname)
        if self.is_configured_interface(interface_event.ifname):
            self.apply()

    async def handle_interface_remove(self, interface_event):
        self.interfaces.remove(interface_event.ifname)
        if self.is_configured_interface(interface_event.ifname):
            self.apply()

    def apply(self):
        config = self.config.data.dhcp.server

        if not config.v4.interface:
            self.stop()
            return

        dhcp4_config = DHCP4Config(config, self.ipam, self.interfaces)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
        json.dump(dhcp4_config.generate(), temp, indent=2)
        temp.flush()
        temp.close()

        shutil.move(temp.name, DHCP4_CONF)

        self.start_unit()

    def start(self):
        self.apply()

    def stop(self):
        self.stop_unit()

    def start_unit(self):
        try:
            self.systemd.start_unit("kea.service")
        except DBusException as e:
            if "NoSuchUnit" in e.get_dbus_name():
                logger.warning("kea.service does not exist. DHCP server will be disabled")
            else:
                raise

    def stop_unit(self):
        try:
            self.systemd.stop_unit("kea.service")
        except DBusException as e:
            if "NoSuchUnit" in e.get_dbus_name():
                logger.warning("kea.service does not exist. DHCP server will be disabled")
            else:
                raise

    def server_command(self, command, **arguments):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(DHCP4_CONTROL_SOCK)
        req = {
            "command": command,
            "arguments": arguments,
        }
        sock.send(json.dumps(req).encode("utf8"))
        data = b""
        while True:
            chunk = sock.recv(SERVER_CHUNK_SIZE)
            data += chunk
            if len(chunk) < SERVER_CHUNK_SIZE:
                break
        return json.loads(data)

    async def rpc_v4_subnet_leases(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> dhcp_server_pb2.DHCPv4LeaseList:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")

        for idx, subnet in enumerate(self.config.staged_data.dhcp.server.v4.subnet):
            if subnet.address == msg.address:
                break
        else:
            raise RPCInvalidArgument(msg.address)

        data = self.server_command("lease4-get-all", subnets=[idx + 1])
        leases = dhcp_server_pb2.DHCPv4LeaseList()
        for lease_data in data["arguments"]["leases"]:
            lease = leases.lease.add()
            lease.hardware_address = lease_data["hw-address"]
            lease.ip_address = lease_data["ip-address"]
            lease.valid_lifetime = lease_data["valid-lft"]
            lease.client_last_transmission_time = lease_data["cltt"]
            lease.hostname = lease_data["hostname"]
            lease.state = lease_data["state"]
        return leases

    async def rpc_v4_config_get(self) -> dhcp_server_pb2.DHCPv4Server:
        return self.config.staged_data.dhcp.server.v4

    async def rpc_v4_config_interface_add(self, msg: dhcp_server_pb2.DHCPv4Server) -> None:
        if not msg.interface:
            raise RPCInvalidArgument("interface not specified")

        for interface in self.config.staged_data.dhcp.server.v4.interface:
            if interface == msg.interface[0]:
                raise RPCInvalidArgument('%s' % msg.interface[0])
        self.config.staged_data.dhcp.server.v4.interface.append(msg.interface[0])

    async def rpc_v4_config_interface_delete(self, msg: dhcp_server_pb2.DHCPv4Server) -> None:
        if not msg.interface:
            raise RPCInvalidArgument("interface not specified")

        for i, interface in enumerate(self.config.staged_data.dhcp.server.v4.interface):
            if interface == msg.interface[0]:
                del self.config.staged_data.dhcp.server.v4.interface[i]

    async def rpc_v4_config_global_settings_update(self, msg: dhcp_server_pb2.DHCPv4Server) -> None:
        self.config.staged_data.dhcp.server.v4.renew_timer = msg.renew_timer
        self.config.staged_data.dhcp.server.v4.rebind_timer = msg.rebind_timer
        self.config.staged_data.dhcp.server.v4.valid_lifetime = msg.valid_lifetime
        self.config.staged_data.dhcp.server.v4.next_server = msg.next_server

    async def rpc_v4_config_option_definition_add(self, msg: dhcp_server_pb2.OptionDefinition) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if not msg.code:
            raise RPCInvalidArgument("code not specified")
        if not msg.type:
            raise RPCInvalidArgument("type not specified")

        for option_definition in self.config.staged_data.dhcp.server.v4.option_definition:
            if option_definition.name == msg.name:
                raise RPCInvalidArgument('%s' % msg.name)
        option_definition = self.config.staged_data.dhcp.server.v4.option_definition.add()
        option_definition.CopyFrom(msg)

    async def rpc_v4_config_option_definition_update(self, msg: dhcp_server_pb2.OptionDefinition) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")

        for option_definition in self.config.staged_data.dhcp.server.v4.option_definition:
            if option_definition.name == msg.name:
                option_definition.CopyFrom(msg)

    async def rpc_v4_config_option_definition_delete(self, msg: dhcp_server_pb2.OptionDefinition) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")

        for i, option_definition in enumerate(self.config.staged_data.dhcp.server.v4.option_definition):
            if option_definition.name == msg.name:
                del self.config.staged_data.dhcp.server.v4.option_definition[i]

    async def rpc_v4_config_client_class_add(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if not msg.test:
            raise RPCInvalidArgument("test not specified")

        for client_class in self.config.staged_data.dhcp.server.v4.client_class:
            if client_class.name == msg.name:
                raise RPCInvalidArgument('%s' % msg.name)
        client_class = self.config.staged_data.dhcp.server.v4.client_class.add()
        client_class.CopyFrom(msg)

    async def rpc_v4_config_client_class_update(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")

        for client_class in self.config.staged_data.dhcp.server.v4.client_class:
            if client_class.name == msg.name:
                client_class.CopyFrom(msg)

    async def rpc_v4_config_client_class_delete(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")

        for i, client_class in enumerate(self.config.staged_data.dhcp.server.v4.client_class):
            if client_class.name == msg.name:
                del self.config.staged_data.dhcp.server.v4.client_class[i]

    async def rpc_v4_config_client_class_option_definition_add(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if len(msg.option_definition) < 1:
            raise RPCInvalidArgument("option_definition not specified")
        if not msg.option_definition[0].name:
            raise RPCInvalidArgument("option_definition.name not specified")
        if not msg.option_definition[0].code:
            raise RPCInvalidArgument("option_definition.code not specified")
        if not msg.option_definition[0].type:
            raise RPCInvalidArgument("option_definition.type not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCInvalidArgument(msg.name)

        for option_definition in client_class.option_definition:
            if option_definition.name == msg.option_definition[0].name:
                raise RPCInvalidArgument('%s' % msg.option_definition[0].name)
        option_definition = client_class.option_definition.add()
        option_definition.CopyFrom(msg.option_definition[0])

    async def rpc_v4_config_client_class_option_definition_update(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if len(msg.option_definition) < 1:
            raise RPCInvalidArgument("option_definition not specified")
        if not msg.option_definition[0].name:
            raise RPCInvalidArgument("option_definition.name not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCInvalidArgument(msg.option_definition[0])

        for option_definition in client_class.option_definition:
            if option_definition.name == msg.option_definition[0].name:
                option_definition.CopyFrom(msg.option_definition[0])

    async def rpc_v4_config_client_class_option_definition_delete(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if len(msg.option_definition) < 1:
            raise RPCInvalidArgument("option_definition not specified")
        if not msg.option_definition[0].name:
            raise RPCInvalidArgument("option_definition.name not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCInvalidArgument(msg.name)

        for i, option_definition in enumerate(client_class.option_definition):
            if option_definition.name == msg.option_definition[0].name:
                del client_class.option_definition[i]

    async def rpc_v4_config_client_class_option_add(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if len(msg.option) < 1:
            raise RPCInvalidArgument("option not specified")
        if not (msg.option[0].name or msg.option[0].code):
            raise RPCInvalidArgument("option.name or option.code not specified")
        if not msg.option[0].data:
            raise RPCInvalidArgument("option.data not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCInvalidArgument(msg.name)

        for option in client_class.option:
            if option.name == msg.option[0].name:
                raise RPCInvalidArgument('%s' % msg.option[0].name)
        option = client_class.option.add()
        option.CopyFrom(msg.option[0])

    async def rpc_v4_config_client_class_option_update(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if len(msg.option) < 1:
            raise RPCInvalidArgument("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidArgument("option.name or option.code not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCInvalidArgument(msg.name)

        for opt in client_class.option:
            if getattr(opt, field) == getattr(option, field):
                opt.CopyFrom(option)

    async def rpc_v4_config_client_class_option_delete(self, msg: dhcp_server_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        if len(msg.option) < 1:
            raise RPCInvalidArgument("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidArgument("option.name or option.code not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCInvalidArgument(msg.name)

        for i, opt in enumerate(client_class.option):
            if getattr(opt, field) == getattr(option, field):
                del client_class.option[i]

    async def rpc_v4_config_option_add(self, msg: dhcp_server_pb2.OptionData) -> None:
        if not (msg.name or msg.code):
            raise RPCInvalidArgument("name or code not specified")
        if not msg.data:
            raise RPCInvalidArgument("data not specified")

        for option in self.config.staged_data.dhcp.server.v4.option:
            if option.name == msg.name:
                raise RPCInvalidArgument('%s' % msg.name)
        option = self.config.staged_data.dhcp.server.v4.option.add()
        option.CopyFrom(msg)

    async def rpc_v4_config_option_update(self, msg: dhcp_server_pb2.OptionData) -> None:
        field = None
        if msg.name:
            field = "name"
        elif msg.code:
            field = "code"

        if not field:
            raise RPCInvalidArgument("name or code not specified")

        for option in self.config.staged_data.dhcp.server.v4.option:
            if getattr(option, field) == getattr(msg, field):
                option.CopyFrom(msg)

    async def rpc_v4_config_option_delete(self, msg: dhcp_server_pb2.OptionData) -> None:
        field = None
        if msg.name:
            field = "name"
        elif msg.code:
            field = "code"

        if not field:
            raise RPCInvalidArgument("name or code not specified")

        for i, option in enumerate(self.config.staged_data.dhcp.server.v4.option):
            if getattr(option, field) == getattr(msg, field):
                del self.config.staged_data.dhcp.server.v4.option[i]

    async def rpc_v4_config_subnet_add(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")

        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                raise RPCInvalidArgument('%s' % msg.address)
        subnet = self.config.staged_data.dhcp.server.v4.subnet.add()
        subnet.CopyFrom(msg)

    async def rpc_v4_config_subnet_update(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")

        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                subnet.CopyFrom(msg)

    async def rpc_v4_config_subnet_delete(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")

        for i, subnet in enumerate(self.config.staged_data.dhcp.server.v4.subnet):
            if subnet.address == msg.address:
                del self.config.staged_data.dhcp.server.v4.subnet[i]

    async def rpc_v4_config_subnet_pool_add(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if not msg.pool:
            raise RPCInvalidArgument("pool not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn
        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for pool in subnet.pool:
            if pool == msg.pool[0]:
                raise RPCInvalidArgument('%s' % msg.pool[0])
        subnet.pool.append(msg.pool[0])

    async def rpc_v4_config_subnet_pool_delete(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if not msg.pool:
            raise RPCInvalidArgument("pool not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn
        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for i, pool in enumerate(subnet.pool):
            if pool == msg.pool[0]:
                del subnet.pool[i]
                break

    async def rpc_v4_config_subnet_option_add(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if len(msg.option) < 1:
            raise RPCInvalidArgument("option not specified")
        if not (msg.option[0].name or msg.option[0].code):
            raise RPCInvalidArgument("option.name or option.code not specified")
        if not msg.option[0].data:
            raise RPCInvalidArgument("option.data not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for option in subnet.option:
            if option.name == msg.option[0].name:
                raise RPCInvalidArgument('%s' % msg.option[0].name)
        option = subnet.option.add()
        option.CopyFrom(msg.option[0])

    async def rpc_v4_config_subnet_option_update(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if len(msg.option) < 1:
            raise RPCInvalidArgument("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidArgument("option.name or option.code not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for opt in subnet.option:
            if getattr(opt, field) == getattr(option, field):
                opt.CopyFrom(option)

    async def rpc_v4_config_subnet_option_delete(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if len(msg.option) < 1:
            raise RPCInvalidArgument("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidArgument("option.name or option.code not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for i, opt in enumerate(subnet.option):
            if getattr(opt, field) == getattr(option, field):
                del subnet.option[i]

    async def rpc_v4_config_subnet_reservation_add(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if len(msg.reservation) < 1:
            raise RPCInvalidArgument("reservation not specified")
        if not msg.reservation[0].hardware_address:
            raise RPCInvalidArgument("reservation.hardware_address not specified")
        if not msg.reservation[0].ip_address:
            raise RPCInvalidArgument("reservation.ip_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for reservation in subnet.reservation:
            if reservation.hardware_address == msg.reservation[0].name:
                raise RPCInvalidArgument('%s' % msg.reservation[0].name)
        reservation = subnet.reservation.add()
        reservation.CopyFrom(msg.reservation[0])

    async def rpc_v4_config_subnet_reservation_update(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if len(msg.reservation) < 1:
            raise RPCInvalidArgument("reservation not specified")
        if not msg.reservation[0].hardware_address:
            raise RPCInvalidArgument("reservation.hardware_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for reservation in subnet.reservation:
            if reservation.hardware_address == msg.reservation[0].hardware_address:
                reservation.CopyFrom(msg.reservation[0])

    async def rpc_v4_config_subnet_reservation_delete(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if len(msg.reservation) < 1:
            raise RPCInvalidArgument("reservation not specified")
        if not msg.reservation[0].hardware_address:
            raise RPCInvalidArgument("reservation.hardware_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for i, reservation in enumerate(subnet.reservation):
            if reservation.hardware_address == msg.reservation[0].hardware_address:
                del subnet.reservation[i]

    async def rpc_v4_config_subnet_relay_address_add(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if not msg.relay_address:
            raise RPCInvalidArgument("relay_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn
        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for relay_address in subnet.relay_address:
            if relay_address == msg.relay_address[0]:
                raise RPCInvalidArgument('%s' % msg.relay_address[0])
        subnet.relay_address.append(msg.relay_address[0])

    async def rpc_v4_config_subnet_relay_address_delete(self, msg: dhcp_server_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidArgument("address not specified")
        if not msg.relay_address:
            raise RPCInvalidArgument("relay_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn
        if not subnet:
            raise RPCInvalidArgument(msg.address)

        for i, relay_address in enumerate(subnet.relay_address):
            if relay_address == msg.relay_address[0]:
                del subnet.relay_address[i]
                break
