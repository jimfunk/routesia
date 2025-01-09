"""
routesia/dns/cache/provider.py - DNS caching with Unbound
"""

import asyncio
from ipaddress import ip_address
import os
import shutil
import tempfile

from routesia.config.configprovider import ConfigProvider
from routesia.dns.dnscacheconfig import (
    DNSCacheLocalConfig,
    DNSCacheForwardConfig,
    LOCAL_CONF,
    FORWARD_CONF,
)
from routesia.service import Provider
from routesia.ipam.ipamprovider import IPAMProvider
from routesia.rpc import RPC
from routesia.netlink.netlinkevents import AddressAddEvent, AddressRemoveEvent
from routesia.schema.v2 import dns_cache_pb2
from routesia.service import Service
from routesia.systemd import SystemdProvider


class DNSCacheProvider(Provider):
    """
    Manages the Unbound caching DNS server.
    """

    ADDRESS_RESTART_DELAY: float = 1
    """
    Delay service restarts for this amount of time after an address change.
    """

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

        self.update_timer: asyncio.TimerHandle | None = None

        self.config.register_change_handler(self.handle_config_change)

        self.service.subscribe_event(AddressAddEvent, self.handle_address_add)
        self.service.subscribe_event(AddressRemoveEvent, self.handle_address_remove)

        self.rpc.register("dns/cache/config/get", self.rpc_config_get)
        self.rpc.register("dns/cache/config/update", self.rpc_config_update)

    async def handle_config_change(self, config):
        self.apply()

    def has_listen_address(self, address):
        "Return True if address is a configured listen address"
        for listen_address in self.config.data.dns.cache.listen_address:
            if ip_address(listen_address.address) == address:
                return True
        return False

    async def handle_address_add(self, address_event):
        if address_event.ip.ip not in self.addresses:
            self.addresses.add(address_event.ip.ip)
            if self.has_listen_address(address_event.ip.ip):
                await self.schedule_apply()

    async def handle_address_remove(self, address_event):
        if address_event.ip.ip in self.addresses:
            self.addresses.remove(address_event.ip.ip)
            if self.has_listen_address(address_event.ip.ip):
                await self.schedule_apply()

    async def schedule_apply(self):
        loop = asyncio.get_running_loop()
        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = loop.call_later(self.ADDRESS_RESTART_DELAY, self.apply)

    def apply(self):
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

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
        os.chmod(LOCAL_CONF, 0o644)

        forward_config = DNSCacheForwardConfig(config)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
        temp.write(forward_config.generate())
        temp.flush()
        temp.close()

        shutil.move(temp.name, FORWARD_CONF)
        os.chmod(FORWARD_CONF, 0o644)

        self.start()

    def start(self):
        self.systemd.start_unit("unbound.service")

    def stop(self):
        self.systemd.stop_unit("unbound.service")

    async def rpc_config_get(self) -> dns_cache_pb2.DNSCacheConfig:
        return self.config.staged_data.dns.cache

    async def rpc_config_update(self, msg: dns_cache_pb2.DNSCacheConfig) -> None:
        self.config.staged_data.dns.cache.CopyFrom(msg)
