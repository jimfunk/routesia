from routesia.interface.eui import EUI
from typing import Any
from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageFlags,
    NetlinkMessageType,
)
from routesia.netlink.rtnetlink.link import (
    AddressFamily,
    InterfaceInfoMessage,
    InterfaceAttribute,
    InterfaceAttributeType,
    InterfaceType,
    InterfaceFlag,
    InterfaceOperationalState,
    InterfaceLinkInfoAttribute,
    InterfaceLinkInfo,
    InterfaceLinkInfoAttributeType,
    ExtMaskFilter,
)
from routesia.netlink import constants


class LinkOperations:
    def __init__(self, socket):
        self.socket = socket

    async def dump(
        self,
        type: InterfaceType | None = None,
        flags: InterfaceFlag | None = None,
        address: EUI | None = None,
        ifname: str | None = None,
        master: int | None = None,
        operstate: InterfaceOperationalState | None = None,
        kind: str | None = None,
        alias: str | None = None,
        altname: str | None = None,
        perm_address: EUI | None = None,
    ) -> list[InterfaceInfoMessage]:
        """
        Get all matching interfaces.
        """
        ifi = InterfaceInfoMessage()
        ifi.attrs.append(
            InterfaceAttribute(
                rta_type=InterfaceAttributeType.IFLA_EXT_MASK,
                payload=ExtMaskFilter.RTEXT_FILTER_VF,
            )
        )

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_DUMP,
            payload=ifi,
        )

        responses = await self.socket.request(msg)
        links = []
        for resp in responses:
            if not isinstance(resp.payload, InterfaceInfoMessage):
                continue
            link = resp.payload
            if type is not None and link.ifi_type != type:
                continue
            if flags is not None and (link.ifi_flags & flags) != flags:
                continue
            if ifname is not None and link.ifname != ifname:
                continue
            if kind is not None and link.kind != kind:
                continue
            if address is not None and link.address != EUI(address):
                continue
            if alias is not None and link.alias != alias:
                continue
            if altname is not None and altname not in link.altnames:
                continue
            if operstate is not None and link.operstate != operstate:
                continue
            if master is not None and link.master != master:
                continue
            if perm_address is not None and link.perm_address != EUI(perm_address):
                continue
            links.append(link)
        return links

    async def get(
        self,
        index: int | None = None,
        ifname: str | None = None,
    ) -> InterfaceInfoMessage | None:
        """
        Get a single interface by index or name.
        """
        ifi = InterfaceInfoMessage()
        ifi.attrs.append(
            InterfaceAttribute(
                rta_type=InterfaceAttributeType.IFLA_EXT_MASK,
                payload=ExtMaskFilter.RTEXT_FILTER_VF,
            )
        )

        if index is not None:
            ifi.ifi_index = index

        if ifname is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_IFNAME, payload=ifname
                )
            )

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST,
            payload=ifi,
        )

        responses = await self.socket.request(msg)
        if responses:
            return responses[0].payload
        return None

    def _base_add_msg(
        self,
        ifname: str,
        index: int | None = None,
        type: InterfaceType | None = None,
        flags: InterfaceFlag | None = None,
        address: EUI | None = None,
        broadcast: EUI | None = None,
        master: int | None = None,
        link: int | None = None,
        mtu: int | None = None,
        txqlen: int | None = None,
        operstate: InterfaceOperationalState | None = None,
        group: int | None = None,
        linkmode: int | None = None,
        alias: str | None = None,
        qdisc: str | None = None,
        promiscuity: int | None = None,
    ) -> InterfaceInfoMessage:
        ifi = InterfaceInfoMessage()

        if index is not None:
            ifi.ifi_index = index

        if type is not None:
            ifi.ifi_type = type

        if flags is not None:
            ifi.ifi_flags = flags
            ifi.ifi_change = flags

        ifi.attrs.append(
            InterfaceAttribute(
                rta_type=InterfaceAttributeType.IFLA_IFNAME, payload=ifname
            )
        )

        if link is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_LINK, payload=int(link)
                )
            )

        if address is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_ADDRESS, payload=address
                )
            )

        if broadcast is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_BROADCAST, payload=broadcast
                )
            )

        if master is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_MASTER, payload=int(master)
                )
            )

        if mtu is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_MTU, payload=int(mtu)
                )
            )

        if txqlen is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_TXQLEN, payload=int(txqlen)
                )
            )

        if operstate is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_OPERSTATE, payload=operstate
                )
            )

        if group is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_GROUP, payload=int(group)
                )
            )

        if linkmode is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_LINKMODE, payload=int(linkmode)
                )
            )

        if alias is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_IFALIAS, payload=alias
                )
            )

        if qdisc is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_QDISC, payload=qdisc
                )
            )

        if promiscuity is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_PROMISCUITY,
                    payload=int(promiscuity),
                )
            )

        return ifi

    def _append_linkinfo(self, ifi: InterfaceInfoMessage, kind: str, data: Any = None):
        lia_kind = InterfaceLinkInfoAttribute(
            rta_type=InterfaceLinkInfoAttributeType.IFLA_INFO_KIND,
            payload=kind,
        )
        attrs = [lia_kind]
        if data is not None:
            lia_data = InterfaceLinkInfoAttribute(
                rta_type=InterfaceLinkInfoAttributeType.IFLA_INFO_DATA
                | constants.NLA_F_NESTED,
                payload=data,
            )
            attrs.append(lia_data)

        li = InterfaceLinkInfo(attrs=attrs)
        ifi.attrs.append(
            InterfaceAttribute(
                rta_type=InterfaceAttributeType.IFLA_LINKINFO | constants.NLA_F_NESTED,
                payload=li,
            )
        )

    async def _send_add_msg(self, ifi: InterfaceInfoMessage) -> None:
        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_NEWLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_CREATE
            | NetlinkMessageFlags.NLM_F_EXCL
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=ifi,
        )
        await self.socket.request(msg)

    async def add_dummy(self, ifname: str, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        self._append_linkinfo(ifi, "dummy")
        await self._send_add_msg(ifi)

    async def add_bridge(self, ifname: str, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        self._append_linkinfo(ifi, "bridge")
        await self._send_add_msg(ifi)

    async def add_vlan(self, ifname: str, link: int, vlan_id: int, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, link=link, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )

        attr = GenericLinkInfoDataAttribute(
            rta_type=1, payload=vlan_id
        )  # IFLA_VLAN_ID = 1
        data = GenericLinkInfoData(attrs=[attr])
        self._append_linkinfo(ifi, "vlan", data)
        await self._send_add_msg(ifi)

    async def add_vxlan(
        self,
        ifname: str,
        vxlan_id: int,
        group: str | None = None,
        local: str | None = None,
        port: int | None = None,
        **kwargs,
    ) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )

        from ipaddress import ip_address

        attrs = []
        attrs.append(
            GenericLinkInfoDataAttribute(rta_type=1, payload=vxlan_id)
        )  # IFLA_VXLAN_ID = 1

        if group:
            ip = ip_address(group)
            rta_type = (
                2 if ip.version == 4 else 17
            )  # IFLA_VXLAN_GROUP or IFLA_VXLAN_GROUP6
            attrs.append(
                GenericLinkInfoDataAttribute(rta_type=rta_type, payload=ip.packed)
            )
        if local:
            ip = ip_address(local)
            rta_type = (
                4 if ip.version == 4 else 18
            )  # IFLA_VXLAN_LOCAL or IFLA_VXLAN_LOCAL6
            attrs.append(
                GenericLinkInfoDataAttribute(rta_type=rta_type, payload=ip.packed)
            )
        if port:
            attrs.append(
                GenericLinkInfoDataAttribute(rta_type=15, payload=port)
            )  # IFLA_VXLAN_PORT

        data = GenericLinkInfoData(attrs=attrs)
        self._append_linkinfo(ifi, "vxlan", data)
        await self._send_add_msg(ifi)

    async def add_sit(
        self, ifname: str, local: str | None = None, remote: str | None = None, **kwargs
    ) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )
        from ipaddress import ip_address

        attrs = []
        if local:
            attrs.append(
                GenericLinkInfoDataAttribute(
                    rta_type=2, payload=ip_address(local).packed
                )
            )  # IFLA_IPTUN_LOCAL
        if remote:
            attrs.append(
                GenericLinkInfoDataAttribute(
                    rta_type=3, payload=ip_address(remote).packed
                )
            )  # IFLA_IPTUN_REMOTE
        data = GenericLinkInfoData(attrs=attrs) if attrs else None
        self._append_linkinfo(ifi, "sit", data)
        await self._send_add_msg(ifi)

    async def add_gre(
        self, ifname: str, local: str | None = None, remote: str | None = None, **kwargs
    ) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )
        from ipaddress import ip_address

        attrs = []
        if local:
            attrs.append(
                GenericLinkInfoDataAttribute(
                    rta_type=6, payload=ip_address(local).packed
                )
            )  # IFLA_GRE_LOCAL
        if remote:
            attrs.append(
                GenericLinkInfoDataAttribute(
                    rta_type=7, payload=ip_address(remote).packed
                )
            )  # IFLA_GRE_REMOTE
        data = GenericLinkInfoData(attrs=attrs) if attrs else None
        self._append_linkinfo(ifi, "gre", data)
        await self._send_add_msg(ifi)

    async def add_bond(self, ifname: str, mode: int | None = None, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )

        attrs = []
        if mode is not None:
            attrs.append(
                GenericLinkInfoDataAttribute(rta_type=1, payload=mode)
            )  # IFLA_BOND_MODE
        data = GenericLinkInfoData(attrs=attrs) if attrs else None
        self._append_linkinfo(ifi, "bond", data)
        await self._send_add_msg(ifi)

    async def add_ifb(self, ifname: str, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        self._append_linkinfo(ifi, "ifb")
        await self._send_add_msg(ifi)

    async def add_ipip(
        self, ifname: str, local: str | None = None, remote: str | None = None, **kwargs
    ) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )
        from ipaddress import ip_address

        attrs = []
        if local:
            attrs.append(
                GenericLinkInfoDataAttribute(
                    rta_type=2, payload=ip_address(local).packed
                )
            )  # IFLA_IPTUN_LOCAL
        if remote:
            attrs.append(
                GenericLinkInfoDataAttribute(
                    rta_type=3, payload=ip_address(remote).packed
                )
            )  # IFLA_IPTUN_REMOTE
        data = GenericLinkInfoData(attrs=attrs) if attrs else None
        self._append_linkinfo(ifi, "ipip", data)
        await self._send_add_msg(ifi)

    async def add_veth(self, ifname: str, peer_name: str, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        peer_ifi = InterfaceInfoMessage()
        peer_ifi.attrs.append(
            InterfaceAttribute(
                rta_type=InterfaceAttributeType.IFLA_IFNAME, payload=peer_name
            )
        )
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )

        # VETH_INFO_PEER = 1
        attr = GenericLinkInfoDataAttribute(rta_type=1, payload=peer_ifi.to_bytes())
        data = GenericLinkInfoData(attrs=[attr])
        self._append_linkinfo(ifi, "veth", data)
        await self._send_add_msg(ifi)

    async def add_vrf(self, ifname: str, table: int, **kwargs) -> None:
        ifi = self._base_add_msg(ifname, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )

        # IFLA_VRF_TABLE = 1
        attr = GenericLinkInfoDataAttribute(rta_type=1, payload=table)
        data = GenericLinkInfoData(attrs=[attr])
        self._append_linkinfo(ifi, "vrf", data)
        await self._send_add_msg(ifi)

    async def add_xfrm(
        self, ifname: str, link: int | None = None, if_id: int | None = None, **kwargs
    ) -> None:
        ifi = self._base_add_msg(ifname, link=link, **kwargs)
        from routesia.netlink.rtnetlink.link import (
            GenericLinkInfoData,
            GenericLinkInfoDataAttribute,
        )

        attrs = []
        # IFLA_XFRM_LINK = 1
        if link is not None:
            attrs.append(GenericLinkInfoDataAttribute(rta_type=1, payload=link))
        # IFLA_XFRM_IF_ID = 2
        if if_id is not None:
            attrs.append(GenericLinkInfoDataAttribute(rta_type=2, payload=if_id))
        data = GenericLinkInfoData(attrs=attrs) if attrs else None
        self._append_linkinfo(ifi, "xfrm", data)
        await self._send_add_msg(ifi)

    async def set(
        self,
        index: int | None = None,
        ifname: str | None = None,
        flags: InterfaceFlag | None = None,
        change: InterfaceFlag | None = None,
        address: EUI | None = None,
        broadcast: EUI | None = None,
        master: int | None = None,
        mtu: int | None = None,
        txqlen: int | None = None,
        operstate: InterfaceOperationalState | None = None,
        group: int | None = None,
        linkmode: int | None = None,
        alias: str | None = None,
        qdisc: str | None = None,
        promiscuity: int | None = None,
    ) -> InterfaceInfoMessage:
        """
        Set interface parameters.
        """
        ifi = InterfaceInfoMessage()

        if index is not None:
            ifi.ifi_index = index

        if ifname is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_IFNAME, payload=ifname
                )
            )

        if flags is not None:
            ifi.ifi_flags = flags
        if change is not None:
            ifi.ifi_change = change

        if address is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_ADDRESS, payload=address
                )
            )

        if broadcast is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_BROADCAST, payload=broadcast
                )
            )

        if master is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_MASTER, payload=int(master)
                )
            )

        if mtu is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_MTU, payload=int(mtu)
                )
            )

        if txqlen is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_TXQLEN, payload=int(txqlen)
                )
            )

        if operstate is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_OPERSTATE, payload=operstate
                )
            )

        if group is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_GROUP, payload=int(group)
                )
            )

        if linkmode is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_LINKMODE, payload=int(linkmode)
                )
            )

        if alias is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_IFALIAS, payload=alias
                )
            )

        if qdisc is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_QDISC, payload=qdisc
                )
            )

        if promiscuity is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_PROMISCUITY,
                    payload=int(promiscuity),
                )
            )

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_SETLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=ifi,
        )

        responses = await self.socket.request(msg)
        if responses:
            return responses[0].payload
        return None

    async def delete(
        self,
        index: int | None = None,
        ifname: str | None = None,
    ):
        """
        Delete an interface.
        """
        ifi = InterfaceInfoMessage()

        if index is not None:
            ifi.ifi_index = index

        if ifname is not None:
            ifi.attrs.append(
                InterfaceAttribute(
                    rta_type=InterfaceAttributeType.IFLA_IFNAME, payload=ifname
                )
            )

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_DELLINK,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=ifi,
        )

        await self.socket.request(msg)
