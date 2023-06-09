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
from routesia.dns.authoritative import authoritative_pb2
from routesia.injector import Provider
from routesia.ipam.provider import IPAMProvider
from routesia.rpc.provider import RPCProvider
from routesia.rtnetlink.events import AddressAddEvent, AddressRemoveEvent
from routesia.server import Server
from routesia.systemd.provider import SystemdProvider


logger = logging.getLogger(__name__)


class AuthoritativeDNSProvider(Provider):
    def __init__(
        self,
        server: Server,
        config: ConfigProvider,
        ipam: IPAMProvider,
        systemd: SystemdProvider,
        rpc: RPCProvider,
    ):
        self.server = server
        self.config = config
        self.ipam = ipam
        self.systemd = systemd
        self.rpc = rpc

        self.addresses = set()

        self.server.subscribe_event(AddressAddEvent, self.handle_address_add)
        self.server.subscribe_event(AddressRemoveEvent, self.handle_address_remove)

    def on_config_change(self, config):
        self.apply()

    def has_listen_address(self, address):
        "Return True if address is a configured listen address"
        for listen_address in self.config.data.dns.authoritative.listen_address:
            if ip_address(listen_address.address) == address:
                return True
        return False

    def handle_address_add(self, address_event):
        self.addresses.add(address_event.ip.ip)
        if self.has_listen_address(address_event.ip.ip):
            self.apply()

    def handle_address_remove(self, address_event):
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
        if not os.path.exists(NSD_SERVER_KEY):
            try:
                # subprocess.run([NSD_CONTROL_SETUP], check_returncode=True)
                subprocess.run([NSD_CONTROL_SETUP])
            except subprocess.CalledProcessError:
                logger.error("nsd-control-setup failed")
        self.systemd.start("nsd.service")

    def stop(self):
        self.systemd.stop("nsd.service")

    def load(self):
        self.config.register_change_handler(self.on_config_change)

    def startup(self):
        self.rpc.register("/dns/authoritative/config/get", self.rpc_config_get)
        self.rpc.register("/dns/authoritative/config/update", self.rpc_config_update)
        self.apply()

    def shutdown(self):
        self.stop()

    def rpc_config_get(self, msg: None) -> authoritative_pb2.AuthoritativeDNSConfig:
        return self.config.staged_data.dns.authoritative

    def rpc_config_update(self, msg: authoritative_pb2.AuthoritativeDNSConfig) -> None:
        self.config.staged_data.dns.authoritative.CopyFrom(msg)
