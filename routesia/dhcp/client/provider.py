"""
routesia/dhcp/client/provider.py - Routesia DHCP clients
"""

from routesia.address.provider import AddressProvider
from routesia.config.provider import ConfigProvider
from routesia.dhcp.client.entities import DHCPv4Client
from routesia.dhcp.client import dhcpclient_pb2
from routesia.exceptions import RPCInvalidParameters, RPCEntityExists, RPCEntityNotFound
from routesia.injector import Provider
from routesia.interface.provider import InterfaceProvider
from routesia.route.provider import RouteProvider
from routesia.rpc.provider import RPCProvider
from routesia.systemd.provider import SystemdProvider


class DHCPClientProvider(Provider):
    def __init__(
        self,
        config: ConfigProvider,
        systemd: SystemdProvider,
        rpc: RPCProvider,
        address_provider: AddressProvider,
        interface_provider: InterfaceProvider,
        route_provider: RouteProvider,
    ):
        self.config = config
        self.systemd = systemd
        self.rpc = rpc
        self.address_provider = address_provider
        self.interface_provider = interface_provider
        self.route_provider = route_provider
        self.v4_clients = {}

    def on_config_change(self, config):
        self.apply()

    def apply(self):
        self.apply_v4()

    def apply_v4(self):
        client_configs = {}

        for client_config in self.config.data.dhcp.client.v4:
            client_configs[client_config.interface] = client_config

        # Remove old ones first
        for interface in list(self.v4_clients.keys()):
            if interface not in client_configs:
                self.v4_clients[interface].stop()
                del self.v4_clients[interface]

        for interface, client_config in client_configs.items():
            if interface in self.v4_clients:
                self.v4_clients[interface].on_config_change(client_config)
            else:
                self.v4_clients[interface] = DHCPv4Client(
                    self.systemd,
                    client_config,
                    self.address_provider,
                    self.interface_provider,
                    self.route_provider,
                )
                self.v4_clients[interface].start()

    def load(self):
        self.config.register_change_handler(self.on_config_change)

    def startup(self):
        self.rpc.register("/dhcp/client/v4/list", self.rpc_v4_list)
        self.rpc.register("/dhcp/client/v4/event", self.rpc_v4_event)
        self.rpc.register("/dhcp/client/v4/restart", self.rpc_v4_restart)
        self.rpc.register("/dhcp/client/config/get", self.rpc_config_get)
        self.rpc.register("/dhcp/client/config/v4/add", self.rpc_config_v4_add)
        self.rpc.register("/dhcp/client/config/v4/update", self.rpc_config_v4_update)
        self.rpc.register("/dhcp/client/config/v4/delete", self.rpc_config_v4_delete)
        self.apply()

    def shutdown(self):
        for client in self.v4_clients.values():
            client.stop()
        self.v4_clients = {}

    def rpc_v4_list(self, msg: None) -> dhcpclient_pb2.DHCPv4ClientStatusList:
        status_list = dhcpclient_pb2.DHCPv4ClientStatusList()
        for client in self.v4_clients.values():
            status = status_list.client.add()
            status.CopyFrom(client.status)
        return status_list

    def rpc_v4_restart(self, msg: dhcpclient_pb2.DHCPv4ClientConfig) -> None:
        if msg.interface not in self.v4_clients:
            return
        self.v4_clients[msg.interface].start()

    def rpc_v4_event(self, msg: dhcpclient_pb2.DHCPv4ClientEvent) -> None:
        if msg.interface not in self.v4_clients:
            return
        self.v4_clients[msg.interface].on_event(msg)

    def rpc_config_get(self, msg: None) -> dhcpclient_pb2.DHCPClientConfig:
        return self.config.staged_data.dhcp.client

    def rpc_config_v4_add(self, msg: dhcpclient_pb2.DHCPv4ClientConfig) -> None:
        if not msg.interface:
            raise RPCInvalidParameters("interface not specified")
        for client in self.config.staged_data.dhcp.client.v4:
            if client.interface == msg.interface:
                raise RPCEntityExists(msg.interface)
        client = self.config.staged_data.dhcp.client.v4.add()
        client.CopyFrom(msg)
        return client

    def rpc_config_v4_update(self, msg: dhcpclient_pb2.DHCPv4ClientConfig) -> None:
        if not msg.interface:
            raise RPCInvalidParameters("interface not specified")
        for client in self.config.staged_data.dhcp.client.v4:
            if client.interface == msg.interface:
                client.CopyFrom(msg)
                return
        raise RPCEntityNotFound(msg.interface)

    def rpc_config_v4_delete(self, msg: dhcpclient_pb2.DHCPv4ClientConfig) -> None:
        if not msg.interface:
            raise RPCInvalidParameters("interface not specified")
        for i, client in enumerate(self.config.staged_data.dhcp.client.v4):
            if client.interface == msg.interface:
                del self.config.staged_data.dhcp.client.v4[i]
                return
        raise RPCEntityNotFound(msg.interface)
