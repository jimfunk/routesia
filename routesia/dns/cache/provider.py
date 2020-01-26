"""
routesia/dns/cache/provider.py - DNS caching with Unbound
"""

import shutil
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dns.cache.config import DNSCacheLocalConfig, DNSCacheForwardConfig, LOCAL_CONF, FORWARD_CONF
from routesia.injector import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.systemd.provider import SystemdProvider


class DNSCacheProvider(Provider):
    def __init__(self, config: ConfigProvider, ipam: IPAMProvider, systemd: SystemdProvider):
        self.config = config
        self.ipam = ipam
        self.systemd = systemd

    def handle_config_update(self, old, new):
        pass

    def apply(self):
        config = self.config.data.dns_cache

        if not config.enabled:
            self.stop()
            return

        local_config = DNSCacheLocalConfig(config, self.ipam)

        temp = tempfile.NamedTemporaryFile(delete=False, mode='w')
        temp.write(local_config.generate())
        temp.flush()
        temp.close()

        shutil.move(temp.name, LOCAL_CONF)

        forward_config = DNSCacheForwardConfig(config)

        temp = tempfile.NamedTemporaryFile(delete=False, mode='w')
        temp.write(forward_config.generate())
        temp.flush()
        temp.close()

        shutil.move(temp.name, FORWARD_CONF)

        self.start()

    def start(self):
        self.systemd.manager.ReloadOrRestartUnit('unbound.service', 'replace')

    def stop(self):
        self.systemd.manager.StopUnit('unbound.service', 'replace')

    def startup(self):
        self.apply()

    def shutdown(self):
        self.stop()
