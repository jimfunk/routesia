"""
routesia/dns/cache/provider.py - DNS caching with Unbound
"""

import shutil
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dns.cache.config import (
    DNSCacheLocalConfig,
    DNSCacheForwardConfig,
    LOCAL_CONF,
    FORWARD_CONF,
)
from routesia.dns.cache import cache_pb2
from routesia.injector import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.rpc.provider import RPCProvider
from routesia.systemd.provider import SystemdProvider


class DNSCacheProvider(Provider):
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
        config = self.config.data.dns.cache

        if not config.enabled:
            self.stop()
            return

        local_config = DNSCacheLocalConfig(config, self.ipam)

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
        self.systemd.manager.ReloadOrRestartUnit("unbound.service", "replace")

    def stop(self):
        self.systemd.manager.StopUnit("unbound.service", "replace")

    def startup(self):
        self.rpc.register("/dns/cache/config/get", self.rpc_config_get)
        self.rpc.register("/dns/cache/config/update", self.rpc_config_update)
        self.apply()

    def shutdown(self):
        self.stop()

    def rpc_config_get(self, msg: None) -> cache_pb2.DNSCacheConfig:
        return self.config.staged_data.dns.cache

    def rpc_config_update(self, msg: cache_pb2.DNSCacheConfig) -> None:
        self.config.staged_data.dns.cache.CopyFrom(msg)
