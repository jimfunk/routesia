"""
routesia/dns/authoritative/config.py - NS2 config
"""

from ipaddress import ip_network
import time


NSD_CONF = '/etc/nsd/nsd.conf'
ZONE_DIR = '/etc/nsd/zones'
NSD_SERVER_KEY = '/etc/nsd/nsd_server.key'
NSD_CONTROL_SETUP = '/usr/sbin/nsd-control-setup'
DEFAULT_TTL = 86400
DEFAULT_REFRESH = 3600
DEFAULT_RETRY = 1800
DEFAULT_EXPIRE = 604800
DEFAULT_MINIMUM_TTL = 86400


class NSDZoneConfig:
    def __init__(self, config, ipam):
        self.config = config
        self.ipam = ipam

    def generate(self):
        domain = '%s.' % self.config.name
        email_user, email_host = self.config.email.split('@', 1)
        email = '%s.%s' % (email_user.replace('.', r'\.'), email_host)
        serial = int(time.time())
        refresh = self.config.refresh if self.config.refresh else DEFAULT_REFRESH
        retry = self.config.retry if self.config.retry else DEFAULT_RETRY
        expire = self.config.expire if self.config.expire else DEFAULT_EXPIRE
        minimum_ttl = self.config.minimum_ttl if self.config.minimum_ttl else DEFAULT_MINIMUM_TTL

        s = '$TTL %s\n' % self.config.ttl if self.config.ttl else DEFAULT_TTL
        s += '$ORIGIN %s\n' % domain
        s += '@ IN SOA %s %s. (%s %s %s %s %s)\n' % (
            domain,
            email,
            serial,
            refresh,
            retry,
            expire,
            minimum_ttl,
        )

        if self.config.use_ipam:
            networks = [ip_network(network) for network in self.config.ipam_network]
            for host in self.ipam.hosts.values():
                for address in host.ip_addresses:
                    for network in networks:
                        if address in network:
                            record_type = 'A' if address.version == 4 else 'AAAA'
                            s += '%s IN %s %s\n' % (
                                host.name,
                                record_type,
                                address,
                            )
                            for alias in host.aliases:
                                s += '%s IN %s %s\n' % (
                                    alias,
                                    record_type,
                                    address,
                                )
                            break

        for record in self.config.record:
            ttl = str(record.ttl) if record.ttl else ''
            s += '%s %s IN %s %s\n' % (
                record.name,
                ttl,
                record.type,
                record.data,
            )

        return s


class NSDConfig:
    def __init__(self, config):
        self.config = config

    def generate(self):
        s = 'server:\n'

        s += '  server-count: %s\n' % (self.config.servers if self.config.servers else 1)

        for listen_address in self.config.listen_address:
            value = listen_address.address
            if listen_address.port:
                value += '@%s' % listen_address.port
            s += '  ip-address: %s\n' % value

        s += '  username: _nsd\n'
        s += '  zonesdir: %s\n' % ZONE_DIR

        s += '''remote-control:
  control-enable: yes
  control-interface: 127.0.0.1
  control-interface: ::1
  control-port: 8952
  server-key-file: "/etc/nsd/nsd_server.key"
  server-cert-file: "/etc/nsd/nsd_server.pem"
  control-key-file: "/etc/nsd/nsd_control.key"
  control-cert-file: "/etc/nsd/nsd_control.pem"
'''

        for zone in self.config.zone:
            s += 'zone:\n'
            s += '  name: %s\n' % zone.name
            s += '  zonefile: %s/%s\n' % (ZONE_DIR, zone.name)

            for notify in zone.notify:
                s += '  notify: %s NOKEY\n' % notify

            for allow_transfer in zone.allow_transfer:
                s += '  provide-xfr: %s NOKEY\n' % allow_transfer

        return s
