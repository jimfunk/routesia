"""
routesia/dns/cache/config.py - Unbound config
"""

from ipaddress import ip_address, ip_network

from routesia.schema.v1 import dns_cache_pb2


LOCAL_CONF = '/etc/unbound/local.d/routesia.conf'
FORWARD_CONF = '/etc/unbound/conf.d/routesia.conf'
TLS_BUNDLE = '/etc/ssl/ca-bundle.pem'


def bool_as_option(b):
    return 'yes' if b else 'no'


class DNSCacheLocalConfig:
    access_control_action_map = {
        dns_cache_pb2.DNSCacheAccessControlRule.DENY: 'deny',
        dns_cache_pb2.DNSCacheAccessControlRule.REFUSE: 'refuse',
        dns_cache_pb2.DNSCacheAccessControlRule.ALLOW: 'allow',
        dns_cache_pb2.DNSCacheAccessControlRule.ALLOW_SET_RECURSION_DESIRED: 'allow_setrd',
        dns_cache_pb2.DNSCacheAccessControlRule.ALLOW_SNOOP: 'allow_snoop',
        dns_cache_pb2.DNSCacheAccessControlRule.DENY_NON_LOCAL: 'deny_non_local',
        dns_cache_pb2.DNSCacheAccessControlRule.REFUSE_NON_LOCAL: 'refuse_non_local',
    }

    local_zone_type_map = {
        dns_cache_pb2.DNSCacheLocalZone.TRANSPARENT: 'transparent',
        dns_cache_pb2.DNSCacheLocalZone.TYPE_TRANSPARENT: 'typetransparent',
        dns_cache_pb2.DNSCacheLocalZone.REDIRECT: 'redirect',
        dns_cache_pb2.DNSCacheLocalZone.INFORM: 'inform',
        dns_cache_pb2.DNSCacheLocalZone.INFORM_DENY: 'inform_deny',
        dns_cache_pb2.DNSCacheLocalZone.INFORM_REDIRECT: 'inform_redirect',
        dns_cache_pb2.DNSCacheLocalZone.DENY: 'deny',
        dns_cache_pb2.DNSCacheLocalZone.REFUSE: 'refuse',
        dns_cache_pb2.DNSCacheLocalZone.ALWAYS_TRANSPARENT: 'always_transparent',
        dns_cache_pb2.DNSCacheLocalZone.ALWAYS_REFUSE: 'always_refuse',
        dns_cache_pb2.DNSCacheLocalZone.ALWAYS_NXDOMAIN: 'always_nxdomain',
        dns_cache_pb2.DNSCacheLocalZone.NO_VIEW: 'noview',
        dns_cache_pb2.DNSCacheLocalZone.NO_DEFAULT: 'nodefault',
    }

    record_type_map = {
        dns_cache_pb2.DNSCacheLocalData.A: 'A',
        dns_cache_pb2.DNSCacheLocalData.AAAA: 'AAAA',
        dns_cache_pb2.DNSCacheLocalData.TXT: 'TXT',
    }

    def __init__(self, config, ipam, addresses):
        self.config = config
        self.ipam = ipam
        self.addresses = addresses

    def generate_interfaces(self):
        s = ''
        for listen_address in self.config.listen_address:
            if ip_address(listen_address.address) in self.addresses:
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
                                for alias in host.aliases:
                                    s += 'local-data: "%s.%s %s IN %s %s"\n' % (
                                        alias,
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
                s += 'local-data: "%s %s IN %s %s"\n' % (
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
