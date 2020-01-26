"""
routesia/ipam/entities.py - IP Address Management entities
"""

from ipaddress import ip_address

from routesia.entity import Entity


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
