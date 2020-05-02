"""
routesia/ipam/provider.py - IP Address Management
"""

from routesia.config.provider import ConfigProvider
from routesia.exceptions import RPCInvalidParameters, RPCEntityExists, RPCEntityNotFound
from routesia.injector import Provider
from routesia.ipam.entities import Host
from routesia.ipam import ipam_pb2
from routesia.rpc.provider import RPCProvider


class IPAMProvider(Provider):
    def __init__(self, config: ConfigProvider, rpc: RPCProvider):
        self.config = config
        self.rpc = rpc
        self.hosts = {}
        self.hosts_by_hardware_address = {}
        self.hosts_by_ip_address = {}

    def update_hosts(self):
        self.hosts = {}
        self.hosts_by_hardware_address = {}
        self.hosts_by_ip_address = {}
        for host_config in self.config.data.ipam.host:
            host = Host(host_config)
            self.hosts[host.name] = host
            if host.hardware_address:
                self.hosts_by_hardware_address[host.hardware_address] = host
            for ip in host.ip_addresses:
                self.hosts_by_ip_address[ip] = host

    def handle_config_update(self, config):
        self.update_hosts()

    def startup(self):
        self.rpc.register("/ipam/config/host/list", self.rpc_config_list)
        self.rpc.register("/ipam/config/host/add", self.rpc_config_host_add)
        self.rpc.register("/ipam/config/host/update", self.rpc_config_host_update)
        self.rpc.register("/ipam/config/host/remove", self.rpc_config_host_remove)
        self.update_hosts()

    def rpc_config_list(self, msg: None) -> ipam_pb2.IPAMConfig:
        return self.config.staged_data.ipam

    def rpc_config_host_add(self, msg: ipam_pb2.Host) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for host in self.config.staged_data.ipam.host:
            if host.name == msg.name:
                raise RPCEntityExists(msg.name)
        host = self.config.staged_data.ipam.host.add()
        host.CopyFrom(msg)

    def rpc_config_host_update(self, msg: ipam_pb2.Host) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for host in self.config.staged_data.ipam.host:
            if host.name == msg.name:
                host.CopyFrom(msg)
                return
        raise RPCEntityNotFound(msg.name)

    def rpc_config_host_remove(self, msg: ipam_pb2.Host) -> None:
        if not msg.name:
            raise RPCInvalidParameters("name not specified")
        for i, host in enumerate(self.config.staged_data.ipam.host):
            if host.name == msg.name:
                del self.config.staged_data.ipam.host[i]
                return
        raise RPCEntityNotFound(msg.name)
