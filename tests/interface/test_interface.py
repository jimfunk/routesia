import pytest

from routesia.interface.interface import Interface, InterfaceState, InterfaceStateChange, InvalidConfig
from routesia.schema.v2.interface_pb2 import InterfaceConfig, InterfaceType, InterfaceLink


async def test_interface_unknown(service, netlink_provider, ip):
    ip.add_dummy_link("foo")

    config = InterfaceConfig()
    config.name = "foo"
    config.type = 9999999

    interface = Interface(config, service, netlink_provider)
    with pytest.raises(InvalidConfig):
        await interface.start()


async def test_interface_start_present(service, netlink_provider, ip):
    ip.add_dummy_link("foo")

    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET

    interface = Interface(config, service, netlink_provider)
    await interface.start()
    assert interface.state == InterfaceState.CONFIGURED
    links = ip.get_links()
    assert "UP" in links["foo"]["flags"]


async def test_interface_start_missing(service, netlink_provider, ip, wait_for):
    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET

    interface = Interface(config, service, netlink_provider)
    await interface.start()
    assert interface.state == InterfaceState.WAITING

    async with await wait_for(InterfaceStateChange, state=InterfaceState.CONFIGURED):
        ip.add_dummy_link("foo")

    links = ip.get_links()
    assert "UP" in links["foo"]["flags"]


async def test_interface_update_disable(service, netlink_provider, ip):
    ip.add_dummy_link("foo")

    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET

    interface = Interface(config, service, netlink_provider)
    await interface.start()
    assert interface.state == InterfaceState.CONFIGURED
    links = ip.get_links()
    assert "UP" in links["foo"]["flags"]

    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET
    config.disable = True

    await interface.handle_config_change(config)

    links = ip.get_links()
    assert "UP" not in links["foo"]["flags"]


async def test_interface_update_link_params(service, netlink_provider, ip):
    ip.add_dummy_link("foo")
    ip.set_link("foo", "arp", "on")
    ip.add_bridge_link("br0")

    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET

    interface = Interface(config, service, netlink_provider)
    await interface.start()
    assert interface.state == InterfaceState.CONFIGURED

    link = ip.get_links(details=True)["foo"]
    assert "NOARP" not in link["flags"]
    assert link["txqlen"] == 1000
    assert link["mtu"] == 1500
    original_address = link["address"]
    assert link["broadcast"] == "ff:ff:ff:ff:ff:ff"
    assert "master" not in link

    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET
    config.link.noarp = True
    config.link.txqueuelen = 5000
    config.link.mtu = 9000
    config.link.address = "00:01:02:aa:bb:cc"
    config.link.broadcast = "ff:ff:ff:00:00:00"
    config.link.master = "br0"

    await interface.handle_config_change(config)

    link = ip.get_links()["foo"]
    assert "NOARP" in link["flags"]
    assert link["txqlen"] == 5000
    assert link["mtu"] == 9000
    assert link["address"] == "00:01:02:aa:bb:cc"
    assert link["broadcast"] == "ff:ff:ff:00:00:00"
    assert link["master"] == "br0"

    config = InterfaceConfig()
    config.name = "foo"
    config.type = InterfaceType.ETHERNET

    await interface.handle_config_change(config)

    link = ip.get_links(details=True)["foo"]
    assert "NOARP" not in link["flags"]
    assert link["txqlen"] == 1000
    assert link["mtu"] == 1500
    assert link["address"] == original_address
    assert link["broadcast"] == "ff:ff:ff:ff:ff:ff"
    assert "master" not in link


@pytest.mark.skip("It would help if pyroute2 supported extack")
async def test_interface_ra_params(service, netlink_provider, ip):
    ip.add_bridge_link("br0")

    config = InterfaceConfig()
    config.name = "br0"
    config.type = InterfaceType.ETHERNET
    config.link.token = "::f2"
    config.link.addrgenmode = InterfaceLink.AddrGenMode.STABLE_PRIVACY

    interface = Interface(config, service, netlink_provider)
    await interface.start()
    assert interface.state == InterfaceState.CONFIGURED
    assert ip.get_token("br0") == "::f2"
    link = ip.get_links(details=True)["br0"]
    assert link["inet6_addr_gen_mode"] == "stable-privacy"

    config = InterfaceConfig()
    config.name = "br0"
    config.type = InterfaceType.ETHERNET

    await interface.handle_config_change(config)

    assert interface.state == InterfaceState.CONFIGURED
    assert ip.get_token("br0") == "::"
    link = ip.get_links(details=True)["br0"]
    assert link["inet6_addr_gen_mode"] == "eui64"


async def test_bridge_interface_start(service, netlink_provider, ip, wait_for):
    config = InterfaceConfig()
    config.name = "br0"
    config.type = InterfaceType.BRIDGE
    config.bridge.stp = True

    interface = Interface(config, service, netlink_provider)

    async with await wait_for(InterfaceStateChange, state=InterfaceState.CONFIGURED):
        await interface.start()

    links = ip.get_links(type="bridge", details=True)
    assert "br0" in links
    assert "UP" in links["br0"]["flags"]
    assert links["br0"]["linkinfo"]["info_data"]["stp_state"] == 1


async def test_bridge_interface_stop(service, netlink_provider, ip, wait_for):
    config = InterfaceConfig()
    config.name = "br0"
    config.type = InterfaceType.BRIDGE

    interface = Interface(config, service, netlink_provider)

    async with await wait_for(InterfaceStateChange, state=InterfaceState.CONFIGURED):
        await interface.start()

    async with await wait_for(InterfaceStateChange, state=InterfaceState.STOPPED):
        await interface.stop()

    assert "br0" not in ip.get_links(type="bridge")
