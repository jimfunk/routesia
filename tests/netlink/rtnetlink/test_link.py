import pytest

from routesia.netlink.socket import NetlinkSocket


async def test_add_dummy(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_dummy(ifname="test_dummy0")

        link = await nl_sock.link.get(ifname="test_dummy0")
        assert link is not None
        assert link.kind == "dummy"


async def test_add_vlan(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_dummy(ifname="test_dummy1")
        link_info = await nl_sock.link.get(ifname="test_dummy1")
        link_idx = link_info.ifi_index

        try:
            await nl_sock.link.add_vlan(
                ifname="test_vlan100", link=link_idx, vlan_id=100
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise

        link = await nl_sock.link.get(ifname="test_vlan100")
        assert link is not None
        assert link.kind == "vlan"


async def test_add_vxlan(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_vxlan(ifname="test_vxlan100", vxlan_id=100)

        link = await nl_sock.link.get(ifname="test_vxlan100")
        assert link is not None
        assert link.kind == "vxlan"


async def test_add_veth(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_veth(ifname="test_veth0", peer_name="test_veth1")

        link0 = await nl_sock.link.get(ifname="test_veth0")
        assert link0 is not None
        assert link0.kind == "veth"

        link1 = await nl_sock.link.get(ifname="test_veth1")
        assert link1 is not None
        assert link1.kind == "veth"


async def test_add_bridge(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_bridge(ifname="test_br0")

        link = await nl_sock.link.get(ifname="test_br0")
        assert link is not None
        assert link.kind == "bridge"


async def test_add_vrf(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_vrf(ifname="test_vrf0", table=1)

        link = await nl_sock.link.get(ifname="test_vrf0")
        assert link is not None
        assert link.kind == "vrf"


async def test_add_sit(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_sit(
            ifname="test_sit1", local="192.168.4.1", remote="192.168.4.2"
        )

        link = await nl_sock.link.get(ifname="test_sit1")
        assert link is not None
        assert link.kind == "sit"


async def test_add_ipip(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_ipip(
            ifname="test_ipip1", local="192.168.2.1", remote="192.168.2.2"
        )

        link = await nl_sock.link.get(ifname="test_ipip1")
        assert link is not None
        assert link.kind == "ipip"


async def test_add_gre(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_gre(
            ifname="test_gre1", local="192.168.3.1", remote="192.168.3.2"
        )

        link = await nl_sock.link.get(ifname="test_gre1")
        assert link is not None
        assert link.kind == "gre"


async def test_add_bond(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_bond(ifname="test_bond0", mode=1)

        link = await nl_sock.link.get(ifname="test_bond0")
        assert link is not None
        assert link.kind == "bond"


async def test_add_ifb(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_ifb(ifname="test_ifb1")

        link = await nl_sock.link.get(ifname="test_ifb1")
        assert link is not None
        assert link.kind == "ifb"


async def test_add_xfrm(netns):
    async with NetlinkSocket() as nl_sock:
        await nl_sock.link.add_dummy(ifname="test_dummy2")
        link_info = await nl_sock.link.get(ifname="test_dummy2")
        link_idx = link_info.ifi_index

        await nl_sock.link.add_xfrm(ifname="test_xfrm0", link=link_idx, if_id=100)

        link = await nl_sock.link.get(ifname="test_xfrm0")
        assert link is not None
        assert link.kind == "xfrm"
