"""
routesia/dhcp/dhcp.py - DHCP support using ISC Kea
"""

from ipaddress import ip_network
import shutil
import tempfile

from routesia.config import ConfigProvider
from routesia.dns.cache import cache_pb2
from routesia.injector import Provider
from routesia.ipam.ipam import IPAMProvider
from routesia.systemd import SystemdProvider


LOCAL_CONF = '/etc/unbound/local.d/routesia.conf'
FORWARD_CONF = '/etc/unbound/conf.d/routesia.conf'
TLS_BUNDLE = '/etc/ssl/ca-bundle.pem'


def bool_as_option(b):
    return 'yes' if b else 'no'


class DNSCacheLocalConfig:
    access_control_action_map = {
        cache_pb2.DNSCacheAccessControlRule.DENY: 'deny',
        cache_pb2.DNSCacheAccessControlRule.REFUSE: 'refuse',
        cache_pb2.DNSCacheAccessControlRule.ALLOW: 'allow',
        cache_pb2.DNSCacheAccessControlRule.ALLOW_SET_RECURSION_DESIRED: 'allow_setrd',
        cache_pb2.DNSCacheAccessControlRule.ALLOW_SNOOP: 'allow_snoop',
        cache_pb2.DNSCacheAccessControlRule.DENY_NON_LOCAL: 'deny_non_local',
        cache_pb2.DNSCacheAccessControlRule.REFUSE_NON_LOCAL: 'refuse_non_local',
    }

    local_zone_type_map = {
        cache_pb2.DNSCacheLocalZone.TRANSPARENT: 'transparent',
        cache_pb2.DNSCacheLocalZone.TYPE_TRANSPARENT: 'typetransparent',
        cache_pb2.DNSCacheLocalZone.REDIRECT: 'redirect',
        cache_pb2.DNSCacheLocalZone.INFORM: 'inform',
        cache_pb2.DNSCacheLocalZone.INFORM_DENY: 'inform_deny',
        cache_pb2.DNSCacheLocalZone.INFORM_REDIRECT: 'inform_redirect',
        cache_pb2.DNSCacheLocalZone.DENY: 'deny',
        cache_pb2.DNSCacheLocalZone.REFUSE: 'refuse',
        cache_pb2.DNSCacheLocalZone.ALWAYS_TRANSPARENT: 'always_transparent',
        cache_pb2.DNSCacheLocalZone.ALWAYS_REFUSE: 'always_refuse',
        cache_pb2.DNSCacheLocalZone.ALWAYS_NXDOMAIN: 'always_nxdomain',
        cache_pb2.DNSCacheLocalZone.NO_VIEW: 'noview',
        cache_pb2.DNSCacheLocalZone.NO_DEFAULT: 'nodefault',
    }

    record_type_map = {
        cache_pb2.DNSCacheLocalData.A: 'A',
        cache_pb2.DNSCacheLocalData.AAAA: 'AAAA',
        cache_pb2.DNSCacheLocalData.TXT: 'TXT',
    }

    def __init__(self, config, ipam):
        self.config = config
        self.ipam = ipam

    def generate_interfaces(self):
        s = ''
        for listen_address in self.config.listen_address:
            port = listen_address.port if listen_address.port else 53
            s += 'interface: %s@%s\n' % (listen_address.address, port)
        return s

    def generate_access_control_rules(self):
        rules = sorted(list(self.config.access_control_rule), key=lambda x: x.priority)
        s = ''
        for rule in rules:
            s += 'access-control: %s %s\n' % (rule.network, self.access_control_action_map[rule.action])
        return s

    def generate_zones(self):
        s = ''
        for zone in self.config.local_zone:
            s += 'local-zone: "%s" %s\n' % (zone.name, self.local_zone_type_map[zone.type])
            zone_ttl = zone.ttl if zone.ttl else self.config.ttl
            if zone.use_ipam:
                networks = [ip_network(network) for network in zone.ipam_network]
                for host in self.ipam.hosts.values():
                    for address in host.ip_addresses:
                        for network in networks:
                            if address in network:
                                record_type = 'A' if address.version == 4 else 'AAAA'
                                s += 'local-data: "%s.%s %s IN %s %s"\n' % (
                                    host.name,
                                    zone.name,
                                    zone_ttl,
                                    record_type,
                                    address,
                                )
                                break

            for local_data in zone.local_data:
                name = local_data.name
                if not name.endswith('.'):
                    name += '.%s' % zone.name
                ttl = local_data.ttl if local_data.ttl else zone_ttl
                s += 'local-data: "%s %s IN %s \'%s\'"\n' % (
                                    name,
                                    ttl,
                                    self.record_type_map[local_data.type],
                                    local_data.data,
                                )
        return s

    def generate(self):
        s = ''
        s += self.generate_interfaces()
        s += self.generate_access_control_rules()

        s += 'tls-upstream: %s\n' % bool_as_option(self.config.tls_upstream)
        s += 'tls-cert-bundle: %s\n' % TLS_BUNDLE

        s += self.generate_zones()

        return s


class DNSCacheForwardConfig:
    def __init__(self, config):
        self.config = config

    def generate(self):
        s = ''

        for zone in self.config.forward_zone:
            s += 'forward-zone:\n'
            s += '  name: "%s"\n' % zone.name
            s += '  forward-tls-upstream: %s\n' % bool_as_option(zone.forward_tls)
            for forward_address in zone.forward_address:
                value = forward_address.address
                if forward_address.port:
                    value += '@%s' % forward_address.port
                if forward_address.host:
                    value += '#%s' % forward_address.host
                s += '  forward-addr: %s\n' % value

        return s


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
