"""
routesia/dhcp/provider.py - DHCP support using ISC Kea
"""

import json
import shutil
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dhcp.server import dhcpserver_pb2
from routesia.dhcp.server.config import DHCP4Config
from routesia.exceptions import RPCInvalidParameters, RPCEntityExists, RPCEntityNotFound
from routesia.injector import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.rpc.provider import RPCProvider
from routesia.systemd.provider import SystemdProvider


DHCP4_CONF = "/etc/kea/kea-dhcp4.conf"
DHCP4_CONTROL_SOCK = "/tmp/kea-dhcp4-ctrl.sock"
DHCP4_LEASE_DB = "/var/lib/kea/dhcp4.leases"


class DHCPServerProvider(Provider):
    def __init__(
        self,
        config: ConfigProvider,
        ipam: IPAMProvider,
        systemd: SystemdProvider,
        rpc: RPCProvider,
    ):
        self.config = config
        self.ipam = ipam
        self.systemd = systemd
        self.rpc = rpc

    def handle_config_update(self, old, new):
        pass

    def apply(self):
        config = self.config.data.dhcp.server

        if not config.v4.interface:
            self.stop()
            return

        dhcp4_config = DHCP4Config(config, self.ipam)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
        json.dump(dhcp4_config.generate(), temp, indent=2)
        temp.flush()
        temp.close()

        shutil.move(temp.name, DHCP4_CONF)

        self.start()

    def start(self):
        self.systemd.manager.ReloadOrRestartUnit("kea.service", "replace")

    def stop(self):
        self.systemd.manager.StopUnit("kea.service", "replace")

    def startup(self):
        self.rpc.register("/dhcp/server/v4/config/get", self.rpc_v4_config_get)
        self.rpc.register("/dhcp/server/v4/config/interface/add", self.rpc_v4_config_interface_add)
        self.rpc.register("/dhcp/server/v4/config/interface/delete", self.rpc_v4_config_interface_delete)
        self.rpc.register("/dhcp/server/v4/config/global_settings/update", self.rpc_v4_config_global_settings_update)
        self.rpc.register("/dhcp/server/v4/config/option_definition/add", self.rpc_v4_config_option_definition_add)
        self.rpc.register("/dhcp/server/v4/config/option_definition/update", self.rpc_v4_config_option_definition_update)
        self.rpc.register("/dhcp/server/v4/config/option_definition/delete", self.rpc_v4_config_option_definition_delete)
        self.rpc.register("/dhcp/server/v4/config/option/add", self.rpc_v4_config_option_add)
        self.rpc.register("/dhcp/server/v4/config/option/update", self.rpc_v4_config_option_update)
        self.rpc.register("/dhcp/server/v4/config/option/delete", self.rpc_v4_config_option_delete)
        self.rpc.register("/dhcp/server/v4/config/client_class/add", self.rpc_v4_config_client_class_add)
        self.rpc.register("/dhcp/server/v4/config/client_class/update", self.rpc_v4_config_client_class_update)
        self.rpc.register("/dhcp/server/v4/config/client_class/delete", self.rpc_v4_config_client_class_delete)
        self.rpc.register("/dhcp/server/v4/config/client_class/option_definition/add", self.rpc_v4_config_client_class_option_definition_add)
        self.rpc.register("/dhcp/server/v4/config/client_class/option_definition/update", self.rpc_v4_config_client_class_option_definition_update)
        self.rpc.register("/dhcp/server/v4/config/client_class/option_definition/delete", self.rpc_v4_config_client_class_option_definition_delete)
        self.rpc.register("/dhcp/server/v4/config/client_class/option/add", self.rpc_v4_config_client_class_option_add)
        self.rpc.register("/dhcp/server/v4/config/client_class/option/update", self.rpc_v4_config_client_class_option_update)
        self.rpc.register("/dhcp/server/v4/config/client_class/option/delete", self.rpc_v4_config_client_class_option_delete)
        self.rpc.register("/dhcp/server/v4/config/subnet/add", self.rpc_v4_config_subnet_add)
        self.rpc.register("/dhcp/server/v4/config/subnet/update", self.rpc_v4_config_subnet_update)
        self.rpc.register("/dhcp/server/v4/config/subnet/delete", self.rpc_v4_config_subnet_delete)
        self.rpc.register("/dhcp/server/v4/config/subnet/pool/add", self.rpc_v4_config_subnet_pool_add)
        self.rpc.register("/dhcp/server/v4/config/subnet/pool/delete", self.rpc_v4_config_subnet_pool_delete)
        self.rpc.register("/dhcp/server/v4/config/subnet/option/add", self.rpc_v4_config_subnet_option_add)
        self.rpc.register("/dhcp/server/v4/config/subnet/option/update", self.rpc_v4_config_subnet_option_update)
        self.rpc.register("/dhcp/server/v4/config/subnet/option/delete", self.rpc_v4_config_subnet_option_delete)
        self.rpc.register("/dhcp/server/v4/config/subnet/reservation/add", self.rpc_v4_config_subnet_reservation_add)
        self.rpc.register("/dhcp/server/v4/config/subnet/reservation/update", self.rpc_v4_config_subnet_reservation_update)
        self.rpc.register("/dhcp/server/v4/config/subnet/reservation/delete", self.rpc_v4_config_subnet_reservation_delete)
        self.apply()

    def shutdown(self):
        self.stop()

    def rpc_v4_config_get(self, msg: None) -> dhcpserver_pb2.DHCPv4Server:
        return self.config.staged_data.dhcp.server.v4

    def rpc_v4_config_interface_add(self, msg: dhcpserver_pb2.DHCPv4Server) -> None:
        if not msg.interface:
            raise RPCInvalidParameters("interface not specified")

        for interface in self.config.staged_data.dhcp.server.v4.interface:
            if interface == msg.interface[0]:
                raise RPCEntityExists('%s' % msg.interface[0])
        self.config.staged_data.dhcp.server.v4.interface.append(msg.interface[0])

    def rpc_v4_config_interface_delete(self, msg: dhcpserver_pb2.DHCPv4Server) -> None:
        if not msg.interface:
            raise RPCInvalidParameters("interface not specified")

        for i, interface in enumerate(self.config.staged_data.dhcp.server.v4.interface):
            if interface.name == msg.interface[0]:
                del self.config.staged_data.dhcp.server.v4.interface[i]

    def rpc_v4_config_global_settings_update(self, msg: dhcpserver_pb2.DHCPv4Server) -> None:
        self.config.staged_data.dhcp.server.v4.renew_timer = msg.renew_timer
        self.config.staged_data.dhcp.server.v4.rebind_timer = msg.rebind_timer
        self.config.staged_data.dhcp.server.v4.valid_lifetime = msg.valid_lifetime
        self.config.staged_data.dhcp.server.v4.next_server = msg.next_server

    def rpc_v4_config_option_definition_add(self, msg: dhcpserver_pb2.OptionDefinition) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if not msg.code:
            raise RPCInvalidParameters("code not specified")
        if not msg.type:
            raise RPCInvalidParameters("type not specified")

        for option_definition in self.config.staged_data.dhcp.server.v4.option_definition:
            if option_definition.name == msg.name:
                raise RPCEntityExists('%s' % msg.name)
        option_definition = self.config.staged_data.dhcp.server.v4.option_definition.add()
        option_definition.CopyFrom(msg)

    def rpc_v4_config_option_definition_update(self, msg: dhcpserver_pb2.OptionDefinition) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")

        for option_definition in self.config.staged_data.dhcp.server.v4.option_definition:
            if option_definition.name == msg.name:
                option_definition.CopyFrom(msg)

    def rpc_v4_config_option_definition_delete(self, msg: dhcpserver_pb2.OptionDefinition) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")

        for i, option_definition in enumerate(self.config.staged_data.dhcp.server.v4.option_definition):
            if option_definition.name == msg.name:
                del self.config.staged_data.dhcp.server.v4.option_definition[i]

    def rpc_v4_config_client_class_add(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if not msg.test:
            raise RPCInvalidParameters("test not specified")

        for client_class in self.config.staged_data.dhcp.server.v4.client_class:
            if client_class.name == msg.name:
                raise RPCEntityExists('%s' % msg.name)
        client_class = self.config.staged_data.dhcp.server.v4.client_class.add()
        client_class.CopyFrom(msg)

    def rpc_v4_config_client_class_update(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")

        for client_class in self.config.staged_data.dhcp.server.v4.client_class:
            if client_class.name == msg.name:
                client_class.CopyFrom(msg)

    def rpc_v4_config_client_class_delete(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")

        for i, client_class in enumerate(self.config.staged_data.dhcp.server.v4.client_class):
            if client_class.name == msg.name:
                del self.config.staged_data.dhcp.server.v4.client_class[i]

    def rpc_v4_config_client_class_option_definition_add(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if len(msg.option_definition) < 1:
            raise RPCInvalidParameters("option_definition not specified")
        if not msg.option_definition[0].name:
            raise RPCInvalidParameters("option_definition.name not specified")
        if not msg.option_definition[0].code:
            raise RPCInvalidParameters("option_definition.code not specified")
        if not msg.option_definition[0].type:
            raise RPCInvalidParameters("option_definition.type not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCEntityNotFound(msg.name)

        for option_definition in client_class.option_definition:
            if option_definition.name == msg.option_definition[0].name:
                raise RPCEntityExists('%s' % msg.option_definition[0].name)
        option_definition = client_class.option_definition.add()
        option_definition.CopyFrom(msg.option_definition[0])

    def rpc_v4_config_client_class_option_definition_update(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if len(msg.option_definition) < 1:
            raise RPCInvalidParameters("option_definition not specified")
        if not msg.option_definition[0].name:
            raise RPCInvalidParameters("option_definition.name not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCEntityNotFound(msg.option_definition[0])

        for option_definition in client_class.option_definition:
            if option_definition.name == msg.option_definition[0].name:
                option_definition.CopyFrom(msg.option_definition[0])

    def rpc_v4_config_client_class_option_definition_delete(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if len(msg.option_definition) < 1:
            raise RPCInvalidParameters("option_definition not specified")
        if not msg.option_definition[0].name:
            raise RPCInvalidParameters("option_definition.name not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCEntityNotFound(msg.name)

        for i, option_definition in enumerate(client_class.option_definition):
            if option_definition.name == msg.option_definition[0].name:
                del client_class.option_definition[i]

    def rpc_v4_config_client_class_option_add(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if len(msg.option) < 1:
            raise RPCInvalidParameters("option not specified")
        if not (msg.option[0].name or msg.option[0].code):
            raise RPCInvalidParameters("option.name or option.code not specified")
        if not msg.option[0].data:
            raise RPCInvalidParameters("option.data not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCEntityNotFound(msg.name)

        for option in client_class.option:
            if option.name == msg.option[0].name:
                raise RPCEntityExists('%s' % msg.option[0].name)
        option = client_class.option.add()
        option.CopyFrom(msg.option[0])

    def rpc_v4_config_client_class_option_update(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if len(msg.option) < 1:
            raise RPCInvalidParameters("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidParameters("option.name or option.code not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCEntityNotFound(msg.name)

        for opt in client_class.option:
            if getattr(opt, field) == getattr(option, field):
                opt.CopyFrom(option)

    def rpc_v4_config_client_class_option_delete(self, msg: dhcpserver_pb2.ClientClass) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        if len(msg.option) < 1:
            raise RPCInvalidParameters("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidParameters("option.name or option.code not specified")

        client_class = None
        for cc in self.config.staged_data.dhcp.server.v4.client_class:
            if cc.name == msg.name:
                client_class = cc

        if not client_class:
            raise RPCEntityNotFound(msg.name)

        for i, opt in enumerate(client_class.option):
            if getattr(opt, field) == getattr(option, field):
                del client_class.option[i]

    def rpc_v4_config_option_add(self, msg: dhcpserver_pb2.OptionData) -> None:
        if not (msg.name or msg.code):
            raise RPCInvalidParameters("name or code not specified")
        if not msg.data:
            raise RPCInvalidParameters("data not specified")

        for option in self.config.staged_data.dhcp.server.v4.option:
            if option.name == msg.name:
                raise RPCEntityExists('%s' % msg.name)
        option = self.config.staged_data.dhcp.server.v4.option.add()
        option.CopyFrom(msg)

    def rpc_v4_config_option_update(self, msg: dhcpserver_pb2.OptionData) -> None:
        field = None
        if msg.name:
            field = "name"
        elif msg.code:
            field = "code"

        if not field:
            raise RPCInvalidParameters("name or code not specified")

        for option in self.config.staged_data.dhcp.server.v4.option:
            if getattr(option, field) == getattr(msg, field):
                option.CopyFrom(msg)

    def rpc_v4_config_option_delete(self, msg: dhcpserver_pb2.OptionData) -> None:
        field = None
        if msg.name:
            field = "name"
        elif msg.code:
            field = "code"

        if not field:
            raise RPCInvalidParameters("name or code not specified")

        for i, option in enumerate(self.config.staged_data.dhcp.server.v4.option):
            if getattr(option, field) == getattr(msg, field):
                del self.config.staged_data.dhcp.server.v4.option[i]

    def rpc_v4_config_subnet_add(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")

        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                raise RPCEntityExists('%s' % msg.address)
        subnet = self.config.staged_data.dhcp.server.v4.subnet.add()
        subnet.CopyFrom(msg)

    def rpc_v4_config_subnet_update(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")

        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                subnet.CopyFrom(msg)

    def rpc_v4_config_subnet_delete(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")

        for i, subnet in enumerate(self.config.staged_data.dhcp.server.v4.subnet):
            if subnet.address == msg.address:
                del self.config.staged_data.dhcp.server.v4.subnet[i]

    def rpc_v4_config_subnet_pool_add(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if not msg.pool:
            raise RPCInvalidParameters("pool not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn
        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for pool in subnet.pool:
            if pool == msg.pool[0]:
                raise RPCEntityExists('%s' % msg.pool[0])
        subnet.pool.append(msg.pool[0])

    def rpc_v4_config_subnet_pool_delete(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if not msg.pool:
            raise RPCInvalidParameters("pool not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn
        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for i, pool in enumerate(subnet.pool):
            if pool == msg.pool[0]:
                del subnet.pool[i]
                break

    def rpc_v4_config_subnet_option_add(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if len(msg.option) < 1:
            raise RPCInvalidParameters("option not specified")
        if not (msg.option[0].name or msg.option[0].code):
            raise RPCInvalidParameters("option.name or option.code not specified")
        if not msg.option[0].data:
            raise RPCInvalidParameters("option.data not specified")

        subnet = None
        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                subnet = subnet

        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for option in subnet.option:
            if option.name == msg.option[0].name:
                raise RPCEntityExists('%s' % msg.option[0].name)
        option = subnet.option.add()
        option.CopyFrom(msg.option[0])

    def rpc_v4_config_subnet_option_update(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if len(msg.option) < 1:
            raise RPCInvalidParameters("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidParameters("option.name or option.code not specified")

        subnet = None
        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                subnet = subnet

        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for opt in subnet.option:
            if getattr(opt, field) == getattr(option, field):
                opt.CopyFrom(option)

    def rpc_v4_config_subnet_option_delete(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if len(msg.option) < 1:
            raise RPCInvalidParameters("option not specified")

        option = msg.option[0]
        field = None
        if option.name:
            field = "name"
        elif option.code:
            field = "code"

        if not field:
            raise RPCInvalidParameters("option.name or option.code not specified")

        subnet = None
        for subnet in self.config.staged_data.dhcp.server.v4.subnet:
            if subnet.address == msg.address:
                subnet = subnet

        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for i, opt in enumerate(subnet.option):
            if getattr(opt, field) == getattr(option, field):
                del subnet.option[i]

    def rpc_v4_config_subnet_reservation_add(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if len(msg.reservation) < 1:
            raise RPCInvalidParameters("reservation not specified")
        if not msg.reservation[0].hardware_address:
            raise RPCInvalidParameters("reservation.hardware_address not specified")
        if not msg.reservation[0].ip_address:
            raise RPCInvalidParameters("reservation.ip_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for reservation in subnet.reservation:
            if reservation.hardware_address == msg.reservation[0].name:
                raise RPCEntityExists('%s' % msg.reservation[0].name)
        reservation = subnet.reservation.add()
        reservation.CopyFrom(msg.reservation[0])

    def rpc_v4_config_subnet_reservation_update(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if len(msg.reservation) < 1:
            raise RPCInvalidParameters("reservation not specified")
        if not msg.reservation[0].hardware_address:
            raise RPCInvalidParameters("reservation.hardware_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for reservation in subnet.reservation:
            if reservation.hardware_address == msg.reservation[0].hardware_address:
                reservation.CopyFrom(msg.reservation[0])

    def rpc_v4_config_subnet_reservation_delete(self, msg: dhcpserver_pb2.DHCPv4Subnet) -> None:
        if not msg.address:
            raise RPCInvalidParameters("address not specified")
        if len(msg.reservation) < 1:
            raise RPCInvalidParameters("reservation not specified")
        if not msg.reservation[0].hardware_address:
            raise RPCInvalidParameters("reservation.hardware_address not specified")

        subnet = None
        for sn in self.config.staged_data.dhcp.server.v4.subnet:
            if sn.address == msg.address:
                subnet = sn

        if not subnet:
            raise RPCEntityNotFound(msg.address)

        for i, reservation in enumerate(subnet.reservation):
            if reservation.hardware_address == msg.reservation[0].hardware_address:
                del subnet.reservation[i]
