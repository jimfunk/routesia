"""
tests/conftrst.py - Routesia test fixtures
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager, suppress
from ctypes import (
    CDLL,
    CFUNCTYPE,
    c_int,
    c_void_p,
    cast,
    create_string_buffer,
    get_errno,
)
import errno
import functools
import inspect
import json
import logging
import os
from paho.mqtt.client import MQTTMessage, topic_matches_sub
import pty
import pytest
import subprocess
import uuid

from routesia.address.provider import AddressProvider
from routesia.cli import CLI
from routesia.config.provider import ConfigProvider
from routesia.mqtt import MQTT
from routesia.netfilter.nftables import Nftables
from routesia.rpc import RPC
from routesia.rpcclient import RPCClient
from routesia.rtnetlink.provider import IPRouteProvider
from routesia.schema.registry import SchemaRegistry
from routesia.service import Service


collect_ignore = ["test_pb2.py"]

libc = CDLL("libc.so.6")

CLONE_NEWNET = 0x40000000
MS_BIND = 4096
MNT_DETACH = 2


logger = logging.getLogger("conftest")


def pytest_configure(config):
    if config.option.logdebug:
        config.option.log_cli_level = "DEBUG"


def pytest_addoption(parser):
    parser.addoption("--logdebug", action="store_true", help="Enable debug logging")


def create_namespace(name):
    if not os.path.isdir("/run/netns"):
        os.mkdir("/run/netns")

    ns_path = f"/run/netns/{name}"

    if os.path.exists(ns_path):
        raise OSError(errno.EEXIST, "Namespace exists")

    with open(ns_path, "w"):
        pass

    def clone_fn():
        libc.mount(b"/proc/self/ns/net", ns_path.encode(), None, MS_BIND, None)
        err = get_errno()
        if err:
            raise OSError(err, f"Could not bind mount namespace: {os.strerror(err)}")
        return err

    stack = create_string_buffer(4096)
    libc.clone(
        CFUNCTYPE(c_int)(clone_fn),
        c_void_p(cast(stack, c_void_p).value + 4096),
        CLONE_NEWNET,
    )


def delete_namespace(name):
    ns_path = f"/run/netns/{name}"

    if not os.path.exists(ns_path):
        raise OSError(errno.ENOENT, "Namespace does not exist")

    libc.umount2(ns_path.encode(), MNT_DETACH)
    err = get_errno()
    if err:
        raise OSError(err, f"Could not unmount namespace: {os.strerror(err)}")
    os.unlink(ns_path)


@contextmanager
def netns_context(name):
    outer_ns = os.open("/proc/self/ns/net", os.O_RDONLY)
    inner_ns = os.open(f"/run/netns/{name}", os.O_RDONLY)
    try:
        libc.setns(inner_ns, CLONE_NEWNET)
        yield
    finally:
        libc.setns(outer_ns, CLONE_NEWNET)
        try:
            os.close(inner_ns)
        except Exception:
            pass
        try:
            os.close(outer_ns)
        except Exception:
            pass


class IPError(Exception):
    pass


class IP:
    """
    Interface to the IP command
    """

    def _ip(self, *args, **kwargs):
        """
        Call ip with arguments.

        ``args`` are passed as positional arguments, followed by ``kwargs``,
        which are unpacked and passed as positional arguments.
        """
        cmd = ["ip", "--json"]
        for arg in args:
            cmd.append(str(arg))
        for key, value in kwargs.items():
            cmd.append(key)
            cmd.append(str(value))

        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise IPError(f"Failed to execute {cmd}:\n{e.stderr}")
        if result.stdout:
            return json.loads(result.stdout)
        return None

    def add_dummy_link(self, name):
        logger.info(f"Adding dummy link {name}")
        return self._ip("link", "add", name, type="dummy")

    def set_link(self, name, *args, **kwargs):
        logger.info(f"Setting link {name} {args} {kwargs}")
        return self._ip("link", "set", name, *args, **kwargs)

    def get_links(self, *args, **kwargs):
        links = {}
        for link in self._ip("link", "show", *args, **kwargs):
            links[link["ifname"]] = link
        return links

    def delete_link(self, name):
        logger.info(f"Deleting link {name}")
        return self._ip("link", "del", name)

    def add_address(self, address, interface, *args, **kwargs):
        logger.info(f"Adding address {address} to {interface} {args} {kwargs}")
        return self._ip("address", "add", address, "dev", interface, *args, **kwargs)

    def delete_address(self, address, interface, *args, **kwargs):
        logger.info(f"Adding address {address} from {interface} {args} {kwargs}")
        return self._ip("address", "del", address, "dev", interface, *args, **kwargs)

    def get_addresses(self, interface, *args, **kwargs):
        addresses = {}
        for address in self._ip("address", "show", "dev", interface, *args, **kwargs)[
            0
        ]["addr_info"]:
            addresses[f"{address['local']}/{address['prefixlen']}"] = address
        return addresses

    def add_route(self, destination, *args, **kwargs):
        logger.info(f"Adding route {destination} {args} {kwargs}")
        return self._ip("route", "add", destination, *args, **kwargs)

    def replace_route(self, destination, *args, **kwargs):
        logger.info(f"Replacing route {destination} {args} {kwargs}")
        return self._ip("route", "replace", destination, *args, **kwargs)

    def delete_route(self, destination, *args, **kwargs):
        logger.info(f"Deleting route {destination} {args} {kwargs}")
        return self._ip("route", "del", destination, *args, **kwargs)


@pytest.fixture
def ip(namespace):
    return IP()


def wrap_async_test(pyfuncitem, test_fn):
    service = pyfuncitem.funcargs.get("service", None)
    mqttbroker = pyfuncitem.funcargs.get("mqttbroker", None)

    @functools.wraps(test_fn)
    def wrapped_async_test(*args, **kwargs):
        async def async_test(*args, **kwargs):
            try:
                async with asyncio.timeout(1):
                    if mqttbroker:
                        await mqttbroker.start()

                    if service:
                        await service.start_background()

                        for name, value in kwargs.items():
                            if inspect.iscoroutine(value):
                                kwargs[name] = await value

                        await service.wait_start()

            except asyncio.TimeoutError:
                pytest.fail("Timed out during service setup")

            try:
                async with asyncio.timeout(5):
                    await test_fn(*args, **kwargs)
            except asyncio.TimeoutError:
                logger.error("Timed out during test execution")
                pytest.fail("Timed out during test execution")

            try:
                async with asyncio.timeout(1):
                    if service:
                        await service.stop_background()

                    if mqttbroker:
                        await mqttbroker.stop()
            except asyncio.TimeoutError:
                pytest.fail("Timed out during service shutdown")

        asyncio.run(async_test(*args, **kwargs))

    return wrapped_async_test


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    is_async = False
    if hasattr(pyfuncitem, "hypothesis"):
        if inspect.iscoroutinefunction(pyfuncitem.obj.hypothesis.inner_test):
            is_async = True
            pyfuncitem.obj.hypothesis.inner_test = wrap_async_test(
                pyfuncitem, pyfuncitem.obj.hypothesis.inner_test
            )
    elif inspect.iscoroutinefunction(pyfuncitem.obj):
        is_async = True
        pyfuncitem.obj = wrap_async_test(pyfuncitem, pyfuncitem.obj)

    if not is_async:
        assert (
            pyfuncitem.funcargs.get("service", None) is None
        ), "Test with service fixture must be a coroutine"


@pytest.fixture
def namespace():
    nsname = str(uuid.uuid4())
    create_namespace(nsname)
    yield nsname
    delete_namespace(nsname)


@pytest.fixture
def namespace_context(namespace):
    with netns_context(namespace):
        yield


class Stdin:
    def __init__(self):
        self.master_fd, self.slave_fd = pty.openpty()
        self.reader = os.fdopen(self.master_fd)
        self.writer = open(os.ttyname(self.slave_fd), "w")

    def close(self):
        self.reader.close()
        self.writer.close()


@pytest.fixture
def stdin():
    stdin = Stdin()
    yield stdin
    stdin.close()


class Stdout:
    def __init__(self):
        self.value = ""
        self.dirty = False

    def write(self, data):
        self.value += data
        self.dirty = True

    def clear(self):
        self.value = ""
        self.dirty = False

    def flush(self):
        self.dirty = False


@pytest.fixture
def stdout():
    return Stdout()


class AnyInteger:
    def __eq__(self, other):
        if isinstance(other, int):
            return True
        return False


@pytest.fixture
def any_integer():
    return AnyInteger()


class EventWaiter:
    def __init__(self, future, **params):
        self.future = future
        self.params = params


class TestService(Service):
    """
    This subclass adds `wait_for_event` which is only useful for tests
    """

    def __init__(self):
        super().__init__()
        self.event_waiters = {}

    @classmethod
    def get_provider_class(cls):
        return Service

    async def handle_event(self, event):
        await super().handle_event(event)
        if event.__class__ in self.event_waiters:
            for waiter in self.event_waiters[event.__class__]:
                for param, value in waiter.params.items():
                    if getattr(event, param) != value:
                        break
                else:
                    waiter.future.set_result(True)

    async def wait_for_event(self, event_class, **params):
        """
        Wait for an event of the given type. If any params are given, wait for
        an event matching the given params.
        """
        waiter = EventWaiter(self.main_loop.create_future(), **params)
        if event_class in self.event_waiters:
            self.event_waiters[event_class].append(waiter)
        else:
            self.event_waiters[event_class] = [waiter]
        await waiter.future
        self.event_waiters[event_class].remove(waiter)
        if not self.event_waiters[event_class]:
            del self.event_waiters[event_class]


@pytest.fixture
def service(namespace_context):
    return TestService()


class EventWatcher:
    def __init__(self, service):
        self.service = service
        self.events = []
        self.waiters = {}

    async def handler(self, event):
        self.events.append(event)
        if event.__class__ in self.waiters:
            self.waiters[event.__class__].set_result(event)

    def subscribe(self, *event_classes):
        for event_class in event_classes:
            self.service.subscribe_event(event_class, self.handler)

    async def wait_for(self, event_class):
        future = self.service.main_loop.create_future()
        self.waiters[event_class] = future
        await future
        del self.waiters[event_class]
        return future.result()


@pytest.fixture
def eventwatcher(service):
    return EventWatcher(service)


@pytest.fixture
def wait_for_event(service):
    @asynccontextmanager
    async def waiter(event_class):
        future = asyncio.get_running_loop().create_future()

        async def handler(event):
            future.set_result(event)

        service.subscribe_event(event_class, handler)
        yield future
        await future

    return waiter


class MockMQTTClient:
    def __init__(self, broker, *args, **kwargs):
        self.broker = broker

    def subscribe(self, topic, qos=0):
        self.broker.subscribe(self, topic)

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.broker.publish(topic, payload)

    def connect(self, host, port=1883, keepalive=60, bind_address=""):
        cb = getattr(self, "on_connect", None)
        if cb:
            cb(self, None, 0, 0)

    def loop_read(self):
        pass

    def loop_write(self):
        pass

    def loop_misc(self) -> int:
        return 0


class MockMQTTBroker:
    def __init__(self):
        self.subscriptions = []
        self.queue = asyncio.Queue()
        self.running = False
        self.task = None

    def get_client(self, *args, **kwargs):
        return MockMQTTClient(self)

    def subscribe(self, client, topic):
        self.subscriptions.append((topic, client))

    def publish(self, topic, payload=None):
        self.queue.put_nowait((topic, payload))

    async def message_handler(self):
        try:
            while self.running:
                topic, payload = await self.queue.get()

                for sub, client in self.subscriptions:
                    if topic_matches_sub(sub, topic):
                        cb = getattr(client, "on_message", None)
                        if cb:
                            msg = MQTTMessage(0, topic.encode())
                            msg.payload = payload
                            cb(client, None, msg)
        except asyncio.CancelledError:
            pass

    async def start(self):
        loop = asyncio.get_running_loop()
        self.running = True
        self.task = loop.create_task(self.message_handler())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            await self.task
            self.task = None


@pytest.fixture
def mqttbroker():
    return MockMQTTBroker()


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
def iproute_provider_deps(service, rpcclient_deps):
    service.add_provider(IPRouteProvider)
    return True


@pytest.fixture
def iproute_provider(service, iproute_provider_deps):
    return service.get_provider(IPRouteProvider)


@pytest.fixture
def config_provider_deps(service, rpc_deps, tmp_path):
    service.add_provider(ConfigProvider, location=tmp_path)
    return True


@pytest.fixture
def config_provider(service, config_provider_deps):
    return service.get_provider(ConfigProvider)


@pytest.fixture
def address_provider_deps(service, iproute_provider_deps, config_provider_deps, rpc_deps):
    service.add_provider(AddressProvider)
    return True


@pytest.fixture
def address_provider(service, address_provider_deps):
    return service.get_provider(AddressProvider)


@pytest.fixture
def nftables(namespace_context):
    yield Nftables()
