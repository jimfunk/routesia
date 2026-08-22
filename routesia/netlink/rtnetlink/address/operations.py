from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily

from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageFlags,
    NetlinkMessageType,
)
from routesia.netlink.rtnetlink.address.message import (
    AddressAttributeType,
    AddressFlag,
    AddressScope,
    IfAddrAttribute,
    IfAddrMessage,
)


class AddressOperations:
    def __init__(self, socket):
        self.socket = socket

    async def dump(
        self,
        family: AddressFamily | None = None,
        index: int | None = None,
    ) -> list[IfAddrMessage]:
        """
        Get addresses with optional kernel-side filtering.
        
        Args:
            family: Address family (AF_INET, AF_INET6, etc.)
            index: Interface index - kernel filters to this interface
        """
        ifi = IfAddrMessage()

        if family is not None:
            ifi.ifa_family = family

        if index is not None:
            ifi.ifa_index = index

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETADDR,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_DUMP,
            payload=ifi,
        )

        responses = await self.socket.request(msg)
        addresses = []
        for resp in responses:
            if not isinstance(resp.payload, IfAddrMessage):
                continue
            addresses.append(resp.payload)
        
        return addresses

    async def get(
        self,
        index: int,
        family: AddressFamily | None = None,
    ) -> list[IfAddrMessage]:
        """
        Get addresses for an interface index.
        
        Args:
            index: Interface index (required)
            family: Address family filter (optional)
            
        Returns:
            List of addresses on the interface (interfaces can have multiple)
        """
        return await self.dump(index=index, family=family)

    def _base_add_msg(
        self,
        family: AddressFamily,
        index: int,
        address: IPv4Address | IPv6Address,
        prefixlen: int = 32,
        scope: AddressScope | None = None,
        flags: AddressFlag | None = None,
        local: IPv4Address | IPv6Address | None = None,
        broadcast: IPv4Address | IPv6Address | None = None,
        label: str | None = None,
        anycast: IPv4Address | IPv6Address | None = None,
        multicast: bytes | None = None,
    ) -> IfAddrMessage:
        """
        Build a base IfAddrMessage for adding an address.
        """
        ifi = IfAddrMessage()
        
        ifi.ifa_family = family
        ifi.ifa_index = index
        ifi.ifa_prefixlen = prefixlen
        
        if scope is not None:
            ifi.ifa_scope = scope
        else:
            # Default scope based on address type
            if isinstance(address, IPv4Address):
                if address.is_loopback:
                    ifi.ifa_scope = AddressScope.RT_SCOPE_HOST
                elif address.is_link_local:
                    ifi.ifa_scope = AddressScope.RT_SCOPE_LINK
                else:
                    ifi.ifa_scope = AddressScope.RT_SCOPE_UNIVERSE
            else:
                if address.is_loopback:
                    ifi.ifa_scope = AddressScope.RT_SCOPE_HOST
                elif address.is_link_local:
                    ifi.ifa_scope = AddressScope.RT_SCOPE_LINK
                else:
                    ifi.ifa_scope = AddressScope.RT_SCOPE_UNIVERSE
        
        if flags is not None:
            ifi.ifa_flags = flags

        # Add local address first - kernel requires IFA_LOCAL for IPv4
        # For non-point-to-point, local equals address
        if local is not None:
            ifi.add_attribute(AddressAttributeType.IFA_LOCAL, local)
        elif family == AddressFamily.AF_INET:
            # IPv4 requires IFA_LOCAL
            ifi.add_attribute(AddressAttributeType.IFA_LOCAL, address)

        # Add address attribute
        ifi.add_attribute(AddressAttributeType.IFA_ADDRESS, address)

        # Add broadcast address for IPv4 (if not provided, calculate it)
        if broadcast is not None:
            ifi.add_attribute(AddressAttributeType.IFA_BROADCAST, broadcast)

        # Add label
        if label is not None:
            ifi.add_attribute(AddressAttributeType.IFA_LABEL, label)

        # Add anycast address
        if anycast is not None:
            ifi.add_attribute(AddressAttributeType.IFA_ANYCAST, anycast)

        # Add multicast address
        if multicast is not None:
            ifi.add_attribute(AddressAttributeType.IFA_MULTICAST, multicast)

        return ifi

    async def _send_add_msg(self, ifi: IfAddrMessage) -> None:
        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_NEWADDR,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_CREATE
            | NetlinkMessageFlags.NLM_F_EXCL
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=ifi,
        )
        await self.socket.request(msg)

    async def add(
        self,
        index: int,
        address: IPv4Address | IPv6Address,
        prefixlen: int | None = None,
        scope: AddressScope | None = None,
        flags: AddressFlag | None = None,
        local: IPv4Address | IPv6Address | None = None,
        broadcast: IPv4Address | IPv6Address | None = None,
        label: str | None = None,
    ) -> None:
        """
        Add an IP address to an interface.
        
        Args:
            index: Interface index
            address: IP address to add
            prefixlen: Prefix length (default: 32 for IPv4, 128 for IPv6)
            scope: Address scope
            flags: Address flags
            local: Local address (for point-to-point)
            broadcast: Broadcast address
            label: Interface label
        """
        # Determine default prefix length
        if prefixlen is None:
            if isinstance(address, IPv4Address):
                prefixlen = 32
            else:
                prefixlen = 128

        # Determine address family
        family = AddressFamily.AF_INET if isinstance(address, IPv4Address) else AddressFamily.AF_INET6

        ifi = self._base_add_msg(
            family=family,
            index=index,
            address=address,
            prefixlen=prefixlen,
            scope=scope,
            flags=flags,
            local=local,
            broadcast=broadcast,
            label=label,
        )

        await self._send_add_msg(ifi)

    async def add_ipv4(
        self,
        index: int,
        address: str | IPv4Address,
        prefixlen: int = 32,
        **kwargs,
    ) -> None:
        """
        Add an IPv4 address to an interface.
        
        Args:
            index: Interface index
            address: IPv4 address string or object
            prefixlen: Prefix length (default: 32)
            **kwargs: Additional arguments passed to add()
        """
        if isinstance(address, str):
            address = IPv4Address(address)
        
        await self.add(index=index, address=address, prefixlen=prefixlen, **kwargs)

    async def add_ipv6(
        self,
        index: int,
        address: str | IPv6Address,
        prefixlen: int = 128,
        **kwargs,
    ) -> None:
        """
        Add an IPv6 address to an interface.
        
        Args:
            index: Interface index
            address: IPv6 address string or object
            prefixlen: Prefix length (default: 128)
            **kwargs: Additional arguments passed to add()
        """
        if isinstance(address, str):
            address = IPv6Address(address)
        
        await self.add(index=index, address=address, prefixlen=prefixlen, **kwargs)

    async def delete(
        self,
        index: int,
        address: IPv4Address | IPv6Address,
        prefixlen: int | None = None,
        family: AddressFamily | None = None,
    ) -> None:
        """
        Delete an IP address from an interface.
        
        Args:
            index: Interface index
            address: IP address to delete
            prefixlen: Prefix length (default: 32 for IPv4, 128 for IPv6)
            family: Address family (auto-detected if not specified)
        """
        # Determine default prefix length
        if prefixlen is None:
            if isinstance(address, IPv4Address):
                prefixlen = 32
            else:
                prefixlen = 128

        # Determine address family if not specified
        if family is None:
            family = AddressFamily.AF_INET if isinstance(address, IPv4Address) else AddressFamily.AF_INET6

        ifi = IfAddrMessage()
        ifi.ifa_family = family
        ifi.ifa_index = index
        ifi.ifa_prefixlen = prefixlen

        # Add IFA_LOCAL first (required for IPv4), then IFA_ADDRESS
        if family == AddressFamily.AF_INET:
            ifi.add_attribute(AddressAttributeType.IFA_LOCAL, address)
        ifi.add_attribute(AddressAttributeType.IFA_ADDRESS, address)

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_DELADDR,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=ifi,
        )

        await self.socket.request(msg)

    async def delete_ipv4(
        self,
        index: int,
        address: str | IPv4Address,
        **kwargs,
    ) -> None:
        """
        Delete an IPv4 address from an interface.
        
        Args:
            index: Interface index
            address: IPv4 address string or object
            **kwargs: Additional arguments passed to delete()
        """
        if isinstance(address, str):
            address = IPv4Address(address)
        
        await self.delete(index=index, address=address, **kwargs)

    async def delete_ipv6(
        self,
        index: int,
        address: str | IPv6Address,
        **kwargs,
    ) -> None:
        """
        Delete an IPv6 address from an interface.
        
        Args:
            index: Interface index
            address: IPv6 address string or object
            **kwargs: Additional arguments passed to delete()
        """
        if isinstance(address, str):
            address = IPv6Address(address)
        
        await self.delete(index=index, address=address, **kwargs)
