from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily

from routesia.interface.eui import EUI
from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageFlags,
    NetlinkMessageType,
)
from routesia.netlink.rtnetlink.neighbor.message import (
    NeighborAttributeType,
    NeighborState,
    NeighborFlag,
    NdAttribute,
    NeighbourMessage,
)
from routesia.netlink.rtnetlink.types import EUI as EUIType


class NeighborOperations:
    def __init__(self, socket):
        self.socket = socket

    async def dump(
        self,
        family: AddressFamily | None = None,
        index: int | None = None,
        state: NeighborState | None = None,
    ) -> list[NeighbourMessage]:
        """
        Get neighbor entries with optional kernel-side filtering.
        
        Args:
            family: Address family (AF_INET for ARP, AF_INET6 for NDP)
            index: Interface index - kernel filters to this interface
            state: Neighbor state filter
        """
        ndm = NeighbourMessage()

        if family is not None:
            ndm.ndm_family = family

        if index is not None:
            ndm.ndm_index = index

        if state is not None:
            ndm.ndm_state = state

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETNEIGH,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_DUMP,
            payload=ndm,
        )

        responses = await self.socket.request(msg)
        neighbors = []
        for resp in responses:
            if not isinstance(resp.payload, NeighbourMessage):
                continue
            neighbors.append(resp.payload)
        
        return neighbors

    async def get(
        self,
        index: int,
        dst: IPv4Address | IPv6Address,
        family: AddressFamily | None = None,
    ) -> NeighbourMessage | None:
        """
        Get a specific neighbor entry.
        
        Args:
            index: Interface index (required)
            dst: Destination IP address (required)
            family: Address family (auto-detected from dst if not specified)
            
        Returns:
            Neighbor entry or None if not found
        """
        if family is None:
            family = AddressFamily.AF_INET if isinstance(dst, IPv4Address) else AddressFamily.AF_INET6

        ndm = NeighbourMessage()
        ndm.ndm_family = family
        ndm.ndm_index = index
        ndm.add_attribute(NeighborAttributeType.NDA_DST, dst)

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETNEIGH,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST,
            payload=ndm,
        )

        responses = await self.socket.request(msg)
        if responses:
            return responses[0].payload
        return None

    def _base_add_msg(
        self,
        family: AddressFamily,
        index: int,
        dst: IPv4Address | IPv6Address,
        lladdr: EUIType | None = None,
        state: NeighborState | None = None,
        flags: NeighborFlag | None = None,
        vlan: int | None = None,
        port: int | None = None,
        vni: int | None = None,
        master: int | None = None,
    ) -> NeighbourMessage:
        """
        Build a base NeighbourMessage for adding/modifying a neighbor.
        """
        ndm = NeighbourMessage()
        
        ndm.ndm_family = family
        ndm.ndm_index = index
        
        if state is not None:
            ndm.ndm_state = state
        
        if flags is not None:
            ndm.ndm_flags = flags

        # Add destination address
        ndm.add_attribute(NeighborAttributeType.NDA_DST, dst)

        # Add link-layer address (MAC for Ethernet)
        if lladdr is not None:
            if isinstance(lladdr, EUI):
                lladdr = bytes(lladdr)
            ndm.add_attribute(NeighborAttributeType.NDA_LLADDR, lladdr)

        # Add VLAN ID
        if vlan is not None:
            ndm.add_attribute(NeighborAttributeType.NDA_VLAN, vlan)

        # Add VXLAN port
        if port is not None:
            ndm.add_attribute(NeighborAttributeType.NDA_PORT, port)

        # Add VXLAN VNI
        if vni is not None:
            ndm.add_attribute(NeighborAttributeType.NDA_VNI, vni)

        # Add master device index
        if master is not None:
            ndm.add_attribute(NeighborAttributeType.NDA_MASTER, master)

        return ndm

    async def _send_add_msg(self, ndm: NeighbourMessage, replace: bool = False) -> None:
        flags = (
            NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK
        )
        if replace:
            flags |= NetlinkMessageFlags.NLM_F_REPLACE
        else:
            flags |= NetlinkMessageFlags.NLM_F_CREATE | NetlinkMessageFlags.NLM_F_EXCL

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_NEWNEIGH,
            nlmsg_flags=flags,
            payload=ndm,
        )
        await self.socket.request(msg)

    async def add(
        self,
        index: int,
        dst: IPv4Address | IPv6Address,
        lladdr: EUIType,
        state: NeighborState = NeighborState.NUD_PERMANENT,
        flags: NeighborFlag | None = None,
        vlan: int | None = None,
        port: int | None = None,
        vni: int | None = None,
        master: int | None = None,
    ) -> None:
        """
        Add a neighbor entry (ARP or NDP).
        
        Args:
            index: Interface index
            dst: Destination IP address
            lladdr: Link-layer address (MAC address)
            state: Neighbor state (default: NUD_PERMANENT for static entry)
            flags: Neighbor flags
            vlan: VLAN ID
            port: VXLAN port
            vni: VXLAN VNI
            master: Master device index
        """
        family = AddressFamily.AF_INET if isinstance(dst, IPv4Address) else AddressFamily.AF_INET6

        ndm = self._base_add_msg(
            family=family,
            index=index,
            dst=dst,
            lladdr=lladdr,
            state=state,
            flags=flags,
            vlan=vlan,
            port=port,
            vni=vni,
            master=master,
        )

        await self._send_add_msg(ndm)

    async def add_ipv4(
        self,
        index: int,
        dst: IPv4Address,
        lladdr: EUIType,
        **kwargs,
    ) -> None:
        """
        Add an IPv4 ARP entry.
        
        Args:
            index: Interface index
            dst: IPv4 address
            lladdr: MAC address
            **kwargs: Additional arguments passed to add()
        """
        await self.add(index=index, dst=dst, lladdr=lladdr, **kwargs)

    async def add_ipv6(
        self,
        index: int,
        dst: IPv6Address,
        lladdr: EUIType,
        **kwargs,
    ) -> None:
        """
        Add an IPv6 NDP entry.
        
        Args:
            index: Interface index
            dst: IPv6 address
            lladdr: MAC address
            **kwargs: Additional arguments passed to add()
        """
        await self.add(index=index, dst=dst, lladdr=lladdr, **kwargs)

    async def replace(
        self,
        index: int,
        dst: IPv4Address | IPv6Address,
        lladdr: EUIType,
        state: NeighborState = NeighborState.NUD_PERMANENT,
        **kwargs,
    ) -> None:
        """
        Replace an existing neighbor entry.
        
        Args:
            index: Interface index
            dst: Destination IP address
            lladdr: Link-layer address
            state: Neighbor state
            **kwargs: Additional arguments passed to add()
        """
        family = AddressFamily.AF_INET if isinstance(dst, IPv4Address) else AddressFamily.AF_INET6

        ndm = self._base_add_msg(
            family=family,
            index=index,
            dst=dst,
            lladdr=lladdr,
            state=state,
            **kwargs,
        )

        await self._send_add_msg(ndm, replace=True)

    async def delete(
        self,
        index: int,
        dst: IPv4Address | IPv6Address,
        family: AddressFamily | None = None,
    ) -> None:
        """
        Delete a neighbor entry.
        
        Args:
            index: Interface index
            dst: Destination IP address
            family: Address family (auto-detected from dst if not specified)
        """
        if family is None:
            family = AddressFamily.AF_INET if isinstance(dst, IPv4Address) else AddressFamily.AF_INET6

        ndm = NeighbourMessage()
        ndm.ndm_family = family
        ndm.ndm_index = index
        ndm.add_attribute(NeighborAttributeType.NDA_DST, dst)

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_DELNEIGH,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=ndm,
        )

        await self.socket.request(msg)

    async def delete_ipv4(
        self,
        index: int,
        dst: IPv4Address,
        **kwargs,
    ) -> None:
        """
        Delete an IPv4 ARP entry.
        
        Args:
            index: Interface index
            dst: IPv4 address
            **kwargs: Additional arguments passed to delete()
        """
        await self.delete(index=index, dst=dst, **kwargs)

    async def delete_ipv6(
        self,
        index: int,
        dst: IPv6Address,
        **kwargs,
    ) -> None:
        """
        Delete an IPv6 NDP entry.
        
        Args:
            index: Interface index
            dst: IPv6 address
            **kwargs: Additional arguments passed to delete()
        """
        await self.delete(index=index, dst=dst, **kwargs)
