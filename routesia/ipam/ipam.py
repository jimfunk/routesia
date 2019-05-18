"""
routesia/ipam/ipam.py - IP Address Management
"""

from ipaddress import ip_address

from routesia.entity import Entity
from routesia.config import ConfigProvider
from routesia.injector import Provider


class Host(Entity):
    def __init__(self, config):
        self.config = config

    @property
    def name(self):
        return self.config.name

    @property
    def hardware_address(self):
        return self.config.hardware_address

    @property
    def ip_addresses(self):
        for ip_config in self.config.ip_address:
            yield ip_address(ip_config)


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
