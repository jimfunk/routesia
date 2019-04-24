"""
routesia/dhcp/dhcp.py - DHCP support using ISC Kea
"""

from ipaddress import ip_network
import json
import shutil
import tempfile

from routesia.config import Config
from routesia.injector import Provider
from routesia.ipam.ipam import IPAMProvider
from routesia.systemd import SystemdProvider


DHCP4_CONF = '/etc/kea/kea-dhcp4.conf'
DHCP4_CONTROL_SOCK = '/tmp/kea-dhcp4-ctrl.sock'
DHCP4_LEASE_DB = '/var/lib/kea/dhcp4.leases'


class DHCP4Config:
    def __init__(self, config, ipam):
        self.config = config
        self.ipam = ipam

    def generate_option_definitions(self, config):
        option_definitions = []
        for option_definition in config:
            option_definition_data = {}
            if not all((option_definition.name, option_definition.code, option_definition.type)):
                # Invalid
                continue
            for field in ('name', 'code', 'type', 'record_types', 'encapsulate'):
                value = getattr(option_definition, field)
                if value:
                    option_definition_data[field] = value
            option_definition_data['array'] = 'true' if option_definition.array else 'false'
            option_definitions.append(option_definition_data)
        return option_definitions

    def generate_options(self, config):
        options = []
        for option in config:
            option_data = {}
            if (not option.name and not option.code) or not option.data:
                # Invalid
                continue
            for field in ('name', 'code', 'data'):
                value = getattr(option, field)
                if value:
                    option_data[field] = value
            options.append(option_data)
        return options

    def generate_client_classes(self, config):
        client_classes = []
        for client_class in config:
            client_class_data = {}
            if not all((client_class.name, client_class.test)):
                # Invalid
                continue
            for field in ('name', 'test', 'next_server'):
                value = getattr(client_class, field)
                if value:
                    client_class_data[field] = value
            if client_class.option_definition:
                client_class_data['option-def'] = self.generate_option_definitions(client_class.option_definition)
            if client_class.option:
                client_class_data['option-data'] = self.generate_options(client_class.option)
            client_classes.append(client_class_data)
        return client_classes

    def get_ipam_reservations(self, subnet):
        reservations = []
        for host in self.ipam.hosts.values():
            if host.hardware_address:
                # Add the first address found in the subnet
                for ip_address in host.ip_addresses:
                    if ip_address in subnet:
                        reservations.append(
                            {
                                'hw-address': host.hardware_address,
                                'ip-address': str(ip_address),
                            }
                        )
                        break
        return reservations

    def generate_subnet(self, config):
        subnet = ip_network(config.address)
        data = {
            'subnet': str(subnet),
        }
        pools = []
        for pool_config in config.pool:
            pools.append({'pool': pool_config})
        data['pools'] = pools

        if config.option:
            data['option-data'] = self.generate_options(config.option)

        reservations = []
        if config.use_ipam:
            reservations.extend(self.get_ipam_reservations(subnet))
        for reservation_config in config.reservation:
            reservations.append(
                {
                    'hw-address': reservation_config.hardware_address,
                    'ip-address': str(reservation_config.ip_address),
                }
            )
        data['reservations'] = reservations

        return data

    def generate_dhcp4(self, config):
        data = {
            'interfaces-config': {
                'interfaces': [str(i) for i in config.interface],
            },
            'control-socket': {
                'socket-type': 'unix',
                'socket-name': DHCP4_CONTROL_SOCK,
            },
            'lease-database': {
                'type': 'memfile',
                'persist': True,
                'name': DHCP4_LEASE_DB,
            },
        }
        if config.renew_timer:
            data['renew-timer'] = config.renew_timer
        if config.rebind_timer:
            data['rebind-timer'] = config.rebind_timer
        if config.valid_lifetime:
            data['valid-lifetime'] = config.valid_lifetime
        if config.next_server:
            data['next-server'] = config.next_server

        if config.option_definition:
            data['option-def'] = self.generate_option_definitions(config.option_definition)

        if config.client_class:
            data['client-classes'] = self.generate_client_classes(config.client_class)

        if config.option:
            data['option-data'] = self.generate_options(config.option)

        subnets = []
        for subnet_config in config.subnet:
            subnets.append(self.generate_subnet(subnet_config))
        data['subnet4'] = subnets

        return data

    def generate(self):
        data = {
            'Dhcp4': self.generate_dhcp4(self.config.v4),
        }
        return data


class DHCPProvider(Provider):
    def __init__(self, config: Config, ipam: IPAMProvider, systemd: SystemdProvider):
        self.config = config
        self.ipam = ipam
        self.systemd = systemd

    def handle_config_update(self, old, new):
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
