"""
routesia/dhcp/config.py - Manage Kea configuration
"""

from ipaddress import ip_network


DHCP4_CONF = '/etc/kea/kea-dhcp4.conf'
DHCP4_CONTROL_SOCK = '/tmp/kea-dhcp4-ctrl.sock'
DHCP4_LEASE_DB = '/var/lib/kea/dhcp4.leases'


class DHCP4Config:
    def __init__(self, config, ipam, interfaces):
        self.config = config
        self.ipam = ipam
        self.interfaces = interfaces

    def generate_option_definitions(self, config):
        option_definitions = []
        for option_definition in config:
            option_definition_data = {}
            if not all((option_definition.name, option_definition.code, option_definition.type)):
                # Invalid
                continue
            for field in ('name', 'code', 'space', 'type', 'record_types', 'encapsulate'):
                value = getattr(option_definition, field)
                if value:
                    option_definition_data[field] = value
            option_definition_data['array'] = option_definition.array
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

        if config.next_server:
            data['next-server'] = config.next_server

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

        relay_addresses = []
        for relay_address in config.relay_address:
            relay_addresses.append(relay_address)
        if relay_addresses:
            data['relay'] = {
                'ip-addresses': relay_addresses,
            }

        return data

    def generate_dhcp4(self, config):
        available_interfaces = []
        for interface in config.interface:
            interface = str(interface)
            if interface in self.interfaces:
                available_interfaces.append(interface)
        data = {
            'interfaces-config': {
                'interfaces': available_interfaces,
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
