"""
routesia/ipam/provider.py - IP Address Management
"""

from routesia.config.provider import ConfigProvider
from routesia.injector import Provider
from routesia.ipam.entities import Host


class IPAMProvider(Provider):
    def __init__(self, config: ConfigProvider):
        self.config = config
        self.hosts = {}
        self.hosts_by_hardware_address = {}
        self.hosts_by_ip_address = {}

    def handle_config_update(self, old, new):
        pass

    def startup(self):
        for host_config in self.config.data.ipam.host:
            host = Host(host_config)
            self.hosts[host.name] = host
            if host.hardware_address:
                self.hosts_by_hardware_address[host.hardware_address] = host
            for ip in host.ip_addresses:
                self.hosts_by_ip_address[ip] = host
