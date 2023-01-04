"""
tests/conftrst.py - Routesia test fixtures
"""

import asyncio
from contextlib import contextmanager
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
import ipaddress
import os
import pyroute2
import pytest
import uuid

from routesia.address.provider import AddressProvider
from routesia.config.provider import ConfigProvider
from routesia.exceptions import EntityNotFound
from routesia.rpc.provider import RPCProvider
from routesia.mqtt import MQTT
from routesia.netfilter.nftables import Nftables
from routesia.rtnetlink.events import (
    AddressAddEvent,
    AddressRemoveEvent,
    InterfaceAddEvent,
    InterfaceRemoveEvent,
)
from routesia.server import Server


libc = CDLL("libc.so.6")

CLONE_NEWNET = 0x40000000
MS_BIND = 4096
MNT_DETACH = 2


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


def wrap_async_test(test_fn):
    @functools.wraps(test_fn)
    def async_test(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_fn(*args, **kwargs))

    return async_test


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if hasattr(pyfuncitem, "hypothesis"):
        if inspect.iscoroutinefunction(pyfuncitem.obj.hypothesis.inner_test):
            pyfuncitem.obj.hypothesis.inner_test = wrap_async_test(pyfuncitem.obj.hypothesis.inner_test)
    elif inspect.iscoroutinefunction(pyfuncitem.obj):
        pyfuncitem.obj = wrap_async_test(pyfuncitem.obj)


class FakeIPRoute:
    def __init__(self):
        self.addresses = []
        self.interface_map = {
            0: "lo",
        }
        self.interface_name_map = {
            "lo": 0,
        }

    def addr(self, cmd, **kwargs):
        if kwargs["index"] not in self.interface_map:
            raise KeyError("Interface with index does not exist")
        if cmd == "add":
            self.addresses.append(kwargs)
        elif cmd == "remove":
            for address in self.addresses:
                if (
                    address["index"] == kwargs["index"] and
                    address["address"] == kwargs["address"] and
                    address["mask"] == kwargs["mask"]
                ):
                    self.addresses.remove(address)
                    break

    def has_address(self, ifname, address):
        if ifname not in self.interface_name_map:
            return False
        index = self.interface_name_map[ifname]
        address = ipaddress.ip_interface(address)
        ip = str(address.ip)
        mask = address.network.prefixlen
        for address in self.addresses:
            if (
                address["index"] == index and
                address["address"] == ip and
                address["mask"] == mask
            ):
                return True
        return False

    def get_interface_name_by_index(self, index):
        try:
            return self.interface_map[index]
        except KeyError:
            raise EntityNotFound("Interface does not exist")

    def get_interface_index_by_name(self, name):
        try:
            return self.interface_name_map[name]
        except KeyError:
            raise EntityNotFound("Interface does not exist")


class FakeIPRouteProvider:
    def __init__(self):
        self.iproute = FakeIPRoute()
        self.rt_proto = 42

    def addr(self, cmd, **kwargs):
        return self.iproute.addr(cmd, **kwargs)

    def _get_interface_message(self, index, name):
        message = pyroute2.netlink.rtnl.ifinfmsg.ifinfmsg()
        message["index"] = index
        message["ifi_type"] = 1
        message["attrs"].append(
            ("IFLA_IFNAME", name),
        )
        return message

    def test_add_interface(self, name):
        "Add fake interface and return the add event"
        index = max(self.iproute.interface_map.keys()) + 1
        self.iproute.interface_map[index] = name
        self.iproute.interface_name_map[name] = index
        return InterfaceAddEvent(self.iproute, self._get_interface_message(index, name))

    def test_remove_interface(self, name):
        "Remove fake interface and return the remove event"
        index = self.iproute.interface_name_map[name]
        del self.iproute.interface_map[index]
        del self.iproute.interface_name_map[name]
        return InterfaceRemoveEvent(self.iproute, self._get_interface_message(index, name))

    def _get_address_message(self, index, address):
        ip = ipaddress.ip_interface(address)
        message = pyroute2.netlink.rtnl.ifaddrmsg.ifaddrmsg()
        message["index"] = index
        message["family"] = 2 if ip.version == 6 else 1
        message["prefixlen"] = ip.network.prefixlen
        message["attrs"].append(
            ("IFA_ADDRESS", str(ip.ip)),
        )
        return message

    def test_add_address(self, ifname, address):
        "Add fake address and return the add event"
        ifindex = self.iproute.interface_name_map[ifname]
        ipinterface = ipaddress.ip_interface(address)
        self.iproute.addr("add", index=ifindex, address=str(
            ipinterface.ip), mask=ipinterface.network.prefixlen)
        return AddressAddEvent(self.iproute, self._get_address_message(ifindex, address))

    def test_remove_address(self, ifname, address):
        "Remove fake address and return the remove event"
        ifindex = self.iproute.interface_name_map[ifname]
        ipinterface = ipaddress.ip_interface(address)
        self.iproute.addr("remove", index=ifindex, address=str(
            ipinterface.ip), mask=ipinterface.network.prefixlen)
        return AddressRemoveEvent(self.iproute, self._get_address_message(ifindex, address))


class FakeMQTTClient:
    def __init__(self):
        self.subscriptions = []

    def subscribe(self, topic):
        self.subscriptions.append(topic)


@pytest.fixture
def server_namespace():
    nsname = str(uuid.uuid4())
    create_namespace(nsname)
    yield nsname
    delete_namespace(nsname)


@pytest.fixture
def server_namespace_context(server_namespace):
    with netns_context(server_namespace):
        yield


@pytest.fixture
def server(server_namespace_context):
    return Server()


@pytest.fixture
def mqtt():
    return MQTT(client=FakeMQTTClient)


@pytest.fixture
def fake_iproute_provider():
    return FakeIPRouteProvider()


@pytest.fixture
def rpc_provider(mqtt):
    return RPCProvider(mqtt=mqtt)


@pytest.fixture
def config_provider(rpc_provider, tmp_path):
    return ConfigProvider(rpc=rpc_provider, location=tmp_path)


@pytest.fixture
def address_provider(server, fake_iproute_provider, config_provider, rpc_provider):
    return AddressProvider(
        server=server,
        iproute=fake_iproute_provider,
        config=config_provider,
        rpc=rpc_provider,
    )


@pytest.fixture
def nftables(server_namespace_context):
    yield Nftables()
