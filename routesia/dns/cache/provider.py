"""
routesia/dns/cache/provider.py - DNS caching with Unbound
"""

from ipaddress import ip_address
import shutil
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dns.cache.config import (
    DNSCacheLocalConfig,
    DNSCacheForwardConfig,
    LOCAL_CONF,
    FORWARD_CONF,
)
from routesia.service import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.rpc import RPC
from routesia.rtnetlink.events import AddressAddEvent, AddressRemoveEvent
from routesia.schema.v1 import dns_cache_pb2
from routesia.service import Service
from routesia.systemd import SystemdProvider


class DNSCacheProvider(Provider):
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

        self.addresses = set()

        self.service.subscribe_event(AddressAddEvent, self.handle_address_add)
        self.service.subscribe_event(AddressRemoveEvent, self.handle_address_remove)
        self.rpc.register("/dns/cache/config/get", self.rpc_config_get)
        self.rpc.register("/dns/cache/config/update", self.rpc_config_update)

    def on_config_change(self, config):
        self.apply()

    def has_listen_address(self, address):
        "Return True if address is a configured listen address"
        for listen_address in self.config.data.dns.cache.listen_address:
            if ip_address(listen_address.address) == address:
                return True
        return False

    async def handle_address_add(self, address_event):
        self.addresses.add(address_event.ip.ip)
        if self.has_listen_address(address_event.ip.ip):
            self.apply()

    async def handle_address_remove(self, address_event):
        self.addresses.remove(address_event.ip.ip)
        if self.has_listen_address(address_event.ip.ip):
            self.apply()

    def apply(self):
        config = self.config.data.dns.cache

        if not config.enabled:
            self.stop()
            return

        local_config = DNSCacheLocalConfig(config, self.ipam, self.addresses)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
        temp.write(local_config.generate())
        temp.flush()
        temp.close()

        shutil.move(temp.name, LOCAL_CONF)

        forward_config = DNSCacheForwardConfig(config)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
        temp.write(forward_config.generate())
        temp.flush()
        temp.close()

        shutil.move(temp.name, FORWARD_CONF)

        self.start()

    def start(self):
        self.systemd.start_unit("unbound.service")

    def stop(self):
        self.systemd.stop_unit("unbound.service")

    def load(self):
        self.config.register_change_handler(self.on_config_change)

    def rpc_config_get(self, msg: None) -> dns_cache_pb2.DNSCacheConfig:
        return self.config.staged_data.dns.cache

    def rpc_config_update(self, msg: dns_cache_pb2.DNSCacheConfig) -> None:
        self.config.staged_data.dns.cache.CopyFrom(msg)
