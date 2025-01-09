"""
Network helpers.
"""

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
import json
import logging
import os
import pytest
import signal
import subprocess
import uuid

from routesia.netfilter.nftables import Nftables


libc = CDLL("libc.so.6")

CLONE_NEWNET = 0x40000000
MS_BIND = 4096
MNT_DETACH = 2


logger = logging.getLogger("conftest-network")


class NetworkNamespace:
    def __init__(self, name):
        pass


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
    pid = libc.clone(
        CFUNCTYPE(c_int)(clone_fn),
        c_void_p(cast(stack, c_void_p).value + 4096),
        CLONE_NEWNET | signal.SIGCHLD,
    )
    os.waitpid(pid, 0)


def delete_namespace(name):
    ns_path = f"/run/netns/{name}"

    if not os.path.exists(ns_path):
        raise OSError(errno.ENOENT, "Namespace does not exist")

    libc.umount2(ns_path.encode(), MNT_DETACH)
    err = get_errno()
    if err:
        raise OSError(err, f"Could not unmount namespace: {os.strerror(err)}")
    os.unlink(ns_path)


def setns(fd: int, nstype: int = 0):
    if libc.setns(fd, nstype):
        err = get_errno()
        raise OSError(err, f"Could not set namespace: {os.strerror(err)}")


@contextmanager
def netns_context(name):
    outer_ns = os.open("/proc/self/ns/net", os.O_RDONLY)
    inner_ns = os.open(f"/run/netns/{name}", os.O_RDONLY)
    try:
        logger.info(f"Entering namespace {name}")
        setns(inner_ns)
        yield
    finally:
        logger.info(f"Exiting namespace {name}")
        setns(outer_ns)
        try:
            os.close(inner_ns)
        except Exception:
            pass
        try:
            os.close(outer_ns)
        except Exception:
            pass


@pytest.fixture
def netns():
    name = str(uuid.uuid4())
    create_namespace(name)

    with netns_context(name):
        yield

    delete_namespace(name)


class IPError(Exception):
    pass


class IP:
    """
    Interface to the IP command
    """

    def _ip(self, *args, details=False, **kwargs):
        """
        Call ip with arguments.

        ``args`` are passed as positional arguments, followed by ``kwargs``,
        which are unpacked and passed as positional arguments.
        """
        cmd = ["ip", "--json"]
        if details:
            cmd.append("--details")
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

    def add_bridge_link(self, name):
        logger.info(f"Adding bridge link {name}")
        return self._ip("link", "add", name, type="bridge")

    def set_link(self, name, *args, **kwargs):
        logger.info(f"Setting link {name} {args} {kwargs}")
        return self._ip("link", "set", name, *args, **kwargs)

    def set_token(self, name, token):
        logger.info(f"Setting link {name} token to {token}")
        return self._ip("token", "set", "dev", name, token)

    def get_token(self, name):
        return self._ip("token", "get", "dev", name)[0]["token"]

    def get_links(self, *args, details=False, **kwargs):
        links = {}
        for link in self._ip("link", "show", *args, details=details, **kwargs):
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
def ip(netns):
    return IP()


@pytest.fixture
def nftables(netns):
    yield Nftables()
