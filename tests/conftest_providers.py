"""
Provider fixtures
"""

import pytest

from routesia.cli import CLI
from routesia.config.configprovider import ConfigProvider
from routesia.mqtt import MQTT
from routesia.rpc import RPC
from routesia.rpcclient import RPCClient
from routesia.netlinkprovider import NetlinkProvider
from routesia.schema.registry import SchemaRegistry


@pytest.fixture
def mqtt_deps(service, mqttbroker):
    service.add_provider(MQTT, client=mqttbroker.get_client)
    return True


@pytest.fixture
def mqtt(service, mqtt_deps):
    return service.get_provider(MQTT)


@pytest.fixture
def schema_registry_deps(service):
    service.add_provider(SchemaRegistry)
    return True


@pytest.fixture
def schema_registry(service, schema_registry_deps):
    return service.get_provider(SchemaRegistry)


@pytest.fixture
def rpc_deps(service, mqtt_deps, schema_registry_deps):
    service.add_provider(RPC)
    return True


@pytest.fixture
def rpc(service, rpc_deps):
    return service.get_provider(RPC)


@pytest.fixture
def rpcclient_deps(service, mqtt_deps, schema_registry_deps):
    service.add_provider(RPCClient)
    return True


@pytest.fixture
def rpcclient(service, rpcclient_deps):
    return service.get_provider(RPCClient)


@pytest.fixture
def cli_deps(service, rpcclient_deps, stdin):
    service.add_provider(CLI, stdin=stdin.reader)
    return True


@pytest.fixture
def cli(service, cli_deps):
    return service.get_provider(CLI)


@pytest.fixture
def netlink_provider_deps(service, rpcclient_deps):
    service.add_provider(NetlinkProvider)
    return True


@pytest.fixture
def netlink_provider(service, netlink_provider_deps):
    return service.get_provider(NetlinkProvider)


@pytest.fixture
def config_provider_deps(service, rpc_deps, tmp_path):
    service.add_provider(ConfigProvider, location=tmp_path)
    return True


@pytest.fixture
def config_provider(service, config_provider_deps):
    return service.get_provider(ConfigProvider)
