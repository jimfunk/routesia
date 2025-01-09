import asyncio
import pytest

from routesia.netlinkprovider import (
    NetlinkInterfaceAddEvent,
    NetlinkInterfaceDeleteEvent,
    NetlinkProvider,
)


@pytest.fixture
def dummy_interfaces(ip):
    """
    Create interfaces to be picked up on startup
    """
    ip.add_dummy_link("foo")
    ip.add_dummy_link("bar")


@pytest.fixture
def dummy_objects(dummy_interfaces):
    pass


@pytest.fixture
def netlink_with_objects(service, dummy_objects):
    netlink = NetlinkProvider(service)
    asyncio.run(netlink.start())
    yield netlink


async def test_netlink_startup(netlink_with_objects, ip):
    links = ip.get_links()
    foo_index = links["foo"]["ifindex"]
    bar_index = links["bar"]["ifindex"]

    # Start manually to pick up the running objects
    assert "foo" in netlink_with_objects.interfaces
    assert foo_index in netlink_with_objects.interfaces_by_index

    foo = netlink_with_objects.interfaces["foo"]
    assert netlink_with_objects.interfaces_by_index[foo_index] == foo
    assert isinstance(foo, NetlinkInterfaceAddEvent)
    assert foo.index == foo_index

    bar = netlink_with_objects.interfaces["bar"]
    assert netlink_with_objects.interfaces_by_index[bar_index] == bar
    assert isinstance(bar, NetlinkInterfaceAddEvent)
    assert bar.index == bar_index


async def test_handle_addlink(netlink_provider: NetlinkProvider, ip, wait_for):
    async with await wait_for(NetlinkInterfaceAddEvent, name="foo") as waiter:
        ip.add_dummy_link("foo")
        foo_index = ip.get_links()["foo"]["ifindex"]

    assert waiter.result.name == "foo"
    assert waiter.result.index == foo_index


async def test_handle_deletelink(netlink_provider: NetlinkProvider, ip, wait_for):
    ip.add_dummy_link("foo")
    foo_index = ip.get_links()["foo"]["ifindex"]

    async with await wait_for(NetlinkInterfaceDeleteEvent, name="foo") as waiter:
        ip.delete_link("foo")

    assert waiter.result.name == "foo"
    assert waiter.result.index == foo_index


async def test_get_interface(netlink_provider: NetlinkProvider, ip):
    ip.add_dummy_link("foo")
    foo_index = ip.get_links()["foo"]["ifindex"]

    link = netlink_provider.get_interface(name="foo")
    assert isinstance(link, NetlinkInterfaceAddEvent)
    assert link.index == foo_index

    link = netlink_provider.get_interface(index=foo_index)
    assert isinstance(link, NetlinkInterfaceAddEvent)
    assert link.index == foo_index

    assert netlink_provider.get_interface(name="bar") is None


async def test_link_set(netlink_provider: NetlinkProvider, ip):
    ip.add_dummy_link("foo")
    assert "UP" not in ip.get_links(dev="foo")["foo"]["flags"]

    await netlink_provider.link_set("foo", state="up")

    assert "UP" in ip.get_links(dev="foo")["foo"]["flags"]


async def test_link_add(netlink_provider: NetlinkProvider, ip):
    await netlink_provider.link_add("br0", kind="bridge")

    assert "br0" in ip.get_links(type="bridge")


async def test_link_delete(netlink_provider: NetlinkProvider, ip):
    ip.add_dummy_link("foo")

    await netlink_provider.link_delete("foo")

    assert "foo" not in ip.get_links()
