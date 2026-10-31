from ipaddress import ip_address

from routesia.dhcp.server.config import DHCP4Config, DHCP4_CONTROL_SOCK
from routesia.schema.v1 import dhcp_server_pb2


class FakeIPAM:
    def __init__(self, hosts=None):
        self.hosts = hosts or {}


class FakeHost:
    def __init__(self, hardware_address, ip_addresses):
        self.hardware_address = hardware_address
        self.ip_addresses = [ip_address(address) for address in ip_addresses]


class FakeConfig:
    def __init__(self, v4):
        self.v4 = v4


def test_generate_interfaces():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    v4.interface.append("eth1")
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["interfaces-config"] == {"interfaces": ["eth0"]}


def test_generate_global_settings():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    v4.renew_timer = 1800
    v4.rebind_timer = 3150
    v4.valid_lifetime = 3600
    v4.next_server = "10.0.0.1"
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["renew-timer"] == 1800
    assert data["Dhcp4"]["rebind-timer"] == 3150
    assert data["Dhcp4"]["valid-lifetime"] == 3600
    assert data["Dhcp4"]["next-server"] == "10.0.0.1"


def test_generate_control_socket():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["control-socket"] == {
        "socket-type": "unix",
        "socket-name": DHCP4_CONTROL_SOCK,
    }


def test_generate_loads_lease_cmds_hook():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    libraries = [hook["library"] for hook in data["Dhcp4"]["hooks-libraries"]]
    assert "/usr/lib64/kea/hooks/libdhcp_lease_cmds.so" in libraries


def test_generate_option_definition():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    option_definition = v4.option_definition.add()
    option_definition.name = "foo"
    option_definition.code = 224
    option_definition.type = "string"
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["option-def"] == [
        {"name": "foo", "code": 224, "type": "string", "array": False}
    ]


def test_generate_option():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    option = v4.option.add()
    option.name = "domain-name-servers"
    option.data = "10.0.0.1"
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["option-data"] == [
        {"name": "domain-name-servers", "data": "10.0.0.1"}
    ]


def test_generate_client_classes():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    client_class = v4.client_class.add()
    client_class.name = "pxe"
    client_class.test = "substring(option[60].hex,0,9) == 'PXEClient'"
    client_class.next_server = "10.0.0.1"
    option_definition = client_class.option_definition.add()
    option_definition.name = "foo"
    option_definition.code = 224
    option_definition.type = "string"
    option = client_class.option.add()
    option.name = "bar"
    option.data = "baz"
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["client-classes"] == [
        {
            "name": "pxe",
            "test": "substring(option[60].hex,0,9) == 'PXEClient'",
            "next-server": "10.0.0.1",
            "option-def": [
                {"name": "foo", "code": 224, "type": "string", "array": False}
            ],
            "option-data": [{"name": "bar", "data": "baz"}],
        }
    ]


def test_generate_subnet():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    subnet = v4.subnet.add()
    subnet.address = "10.0.0.0/24"
    subnet.pool.append("10.0.0.100-10.0.0.200")
    subnet.next_server = "10.0.0.1"
    option = subnet.option.add()
    option.name = "routers"
    option.data = "10.0.0.1"
    reservation = subnet.reservation.add()
    reservation.hardware_address = "aa:bb:cc:dd:ee:ff"
    reservation.ip_address = "10.0.0.50"
    subnet.relay_address.append("10.0.0.254")
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert data["Dhcp4"]["subnet4"] == [
        {
            "id": 1,
            "subnet": "10.0.0.0/24",
            "next-server": "10.0.0.1",
            "pools": [{"pool": "10.0.0.100-10.0.0.200"}],
            "option-data": [{"name": "routers", "data": "10.0.0.1"}],
            "reservations": [
                {"hw-address": "aa:bb:cc:dd:ee:ff", "ip-address": "10.0.0.50"}
            ],
            "relay": {"ip-addresses": ["10.0.0.254"]},
        }
    ]


def test_generate_subnet_ids_increment():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    for address in ("10.0.0.0/24", "10.1.0.0/24"):
        subnet = v4.subnet.add()
        subnet.address = address
    data = DHCP4Config(FakeConfig(v4), FakeIPAM(), ("eth0",)).generate()
    assert [subnet["id"] for subnet in data["Dhcp4"]["subnet4"]] == [1, 2]


def test_generate_ipam_reservations():
    v4 = dhcp_server_pb2.DHCPv4Server()
    v4.interface.append("eth0")
    subnet = v4.subnet.add()
    subnet.address = "10.0.0.0/24"
    subnet.use_ipam = True
    ipam = FakeIPAM(
        {
            "host1": FakeHost("aa:bb:cc:dd:ee:ff", ["10.1.0.10", "10.0.0.10"]),
            "host2": FakeHost("", ["10.0.0.11"]),
        }
    )
    data = DHCP4Config(FakeConfig(v4), ipam, ("eth0",)).generate()
    assert data["Dhcp4"]["subnet4"][0]["reservations"] == [
        {"hw-address": "aa:bb:cc:dd:ee:ff", "ip-address": "10.0.0.10"}
    ]
