"""
routesia/dhcp/provider.py - DHCP support using ISC Kea
"""

import json
import shutil
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dhcp.config import DHCP4Config
from routesia.injector import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.systemd.provider import SystemdProvider


DHCP4_CONF = '/etc/kea/kea-dhcp4.conf'
DHCP4_CONTROL_SOCK = '/tmp/kea-dhcp4-ctrl.sock'
DHCP4_LEASE_DB = '/var/lib/kea/dhcp4.leases'


class DHCPClientProvider(Provider):
    def __init__(self, config: ConfigProvider, ipam: IPAMProvider, systemd: SystemdProvider):
        self.config = config
        self.ipam = ipam
        self.systemd = systemd

    def handle_config_update(self, config):
        pass

    def apply(self):
        config = self.config.data.dhcp

        if not config.v4.interface:
            self.stop()
            return

        dhcp4_config = DHCP4Config(config, self.ipam)

        temp = tempfile.NamedTemporaryFile(delete=False, mode='w')
        json.dump(dhcp4_config.generate(), temp, indent=2)
        temp.flush()
        temp.close()

        shutil.move(temp.name, DHCP4_CONF)

        self.start()

    def start(self):
        self.systemd.manager.ReloadOrRestartUnit('kea.service', 'replace')

    def stop(self):
        self.systemd.manager.StopUnit('kea.service', 'replace')

    def startup(self):
        self.apply()

    def shutdown(self):
        self.stop()
