"""
routesia/ipam/provider.py - IP Address Management
"""

from routesia.config.configprovider import ConfigProvider
from routesia.rpc import RPCInvalidArgument
from routesia.service import Provider
from routesia.ipam.ipamentities import Host
from routesia.rpc import RPC
from routesia.schema.v2 import ipam_pb2


class IPAMProvider(Provider):
    def __init__(self, config: ConfigProvider, rpc: RPC):
        self.config = config
        self.rpc = rpc
        self.hosts = {}
        self.hosts_by_hardware_address = {}
        self.hosts_by_ip_address = {}

        self.config.register_change_handler(self.handle_config_change)

        self.rpc.register("ipam/config/host/list", self.rpc_config_list)
        self.rpc.register("ipam/config/host/add", self.rpc_config_host_add)
        self.rpc.register("ipam/config/host/update", self.rpc_config_host_update)
        self.rpc.register("ipam/config/host/remove", self.rpc_config_host_remove)

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

    async def handle_config_change(self, config):
        self.update_hosts()

    def start(self):
        self.update_hosts()

    async def rpc_config_list(self) -> ipam_pb2.IPAMConfig:
        return self.config.staged_data.ipam

    async def rpc_config_host_add(self, msg: ipam_pb2.Host) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        for host in self.config.staged_data.ipam.host:
            if host.name == msg.name:
                raise RPCInvalidArgument(msg.name)
        host = self.config.staged_data.ipam.host.add()
        host.CopyFrom(msg)

    async def rpc_config_host_update(self, msg: ipam_pb2.Host) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        for host in self.config.staged_data.ipam.host:
            if host.name == msg.name:
                host.CopyFrom(msg)
                return
        raise RPCInvalidArgument(msg.name)

    async def rpc_config_host_remove(self, msg: ipam_pb2.Host) -> None:
        if not msg.name:
            raise RPCInvalidArgument("name not specified")
        for i, host in enumerate(self.config.staged_data.ipam.host):
            if host.name == msg.name:
                del self.config.staged_data.ipam.host[i]
                return
        raise RPCInvalidArgument(msg.name)
