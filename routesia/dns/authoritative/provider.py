"""
routesia/dns/authoritative/provider.py - Authoritative DNS using NS2
"""

from ipaddress import ip_address
import logging
import os
import shutil
import subprocess
import tempfile

from routesia.config.provider import ConfigProvider
from routesia.dns.authoritative.config import (
    NSDConfig,
    NSDZoneConfig,
    NSD_CONF,
    ZONE_DIR,
    NSD_SERVER_KEY,
    NSD_CONTROL_SETUP,
)
from routesia.service import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.rpc import RPC
from routesia.rtnetlink.events import AddressAddEvent, AddressRemoveEvent
from routesia.schema.v1 import dns_authoritative_pb2
from routesia.service import Service
from routesia.systemd import SystemdProvider


logger = logging.getLogger("dns-authoritative")


class AuthoritativeDNSProvider(Provider):
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
        self.rpc.register("/dns/authoritative/config/get", self.rpc_config_get)
        self.rpc.register("/dns/authoritative/config/update", self.rpc_config_update)

    def on_config_change(self, config):
        self.apply()

    def has_listen_address(self, address):
        "Return True if address is a configured listen address"
        for listen_address in self.config.data.dns.authoritative.listen_address:
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
        config = self.config.data.dns.authoritative

        if not config.enabled:
            self.stop()
            return

        nsd_config = NSDConfig(config, self.addresses)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
        temp.write(nsd_config.generate())
        temp.flush()
        temp.close()
        os.chmod(temp.name, 0o644)

        shutil.move(temp.name, NSD_CONF)

        for zone in config.zone:
            zone_config = NSDZoneConfig(zone, self.ipam)

            temp = tempfile.NamedTemporaryFile(delete=False, mode="w")
            temp.write(zone_config.generate())
            temp.flush()
            temp.close()
            os.chmod(temp.name, 0o644)

            shutil.move(temp.name, "%s/%s" % (ZONE_DIR, zone.name))

        self.start()

    def start(self):
        self.apply()
        if not os.path.exists(NSD_SERVER_KEY):
            try:
                # subprocess.run([NSD_CONTROL_SETUP], check_returncode=True)
                subprocess.run([NSD_CONTROL_SETUP])
            except subprocess.CalledProcessError:
                logger.error("nsd-control-setup failed")
        self.systemd.start_unit("nsd.service")

    def stop(self):
        self.systemd.stop_unit("nsd.service")

    def load(self):
        self.config.register_change_handler(self.on_config_change)

    def rpc_config_get(self, msg: None) -> dns_authoritative_pb2.AuthoritativeDNSConfig:
        return self.config.staged_data.dns.authoritative

    def rpc_config_update(self, msg: dns_authoritative_pb2.AuthoritativeDNSConfig) -> None:
        self.config.staged_data.dns.authoritative.CopyFrom(msg)
