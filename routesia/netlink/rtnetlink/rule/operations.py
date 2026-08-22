from ipaddress import IPv4Address, IPv6Address
from socket import AddressFamily

from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageFlags,
    NetlinkMessageType,
)
from routesia.netlink.rtnetlink.rule.message import (
    RuleAttributeType,
    RuleAction,
    RuleFlag,
    RuleMessage,
)


class RuleOperations:
    def __init__(self, socket):
        self.socket = socket

    async def dump(
        self,
        family: AddressFamily | None = None,
    ) -> list[RuleMessage]:
        """
        Get routing rules with optional kernel-side filtering.
        
        Args:
            family: Address family (AF_INET, AF_INET6, etc.)
        """
        rule = RuleMessage()

        if family is not None:
            rule.rtm_family = family

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_GETRULE,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_DUMP,
            payload=rule,
        )

        responses = await self.socket.request(msg)
        rules = []
        for resp in responses:
            if not isinstance(resp.payload, RuleMessage):
                continue
            rules.append(resp.payload)
        
        return rules

    def _base_add_msg(
        self,
        family: AddressFamily,
        table: int | None = None,
        action: RuleAction = RuleAction.FR_ACT_TO_TBL,
        priority: int | None = None,
        dst: IPv4Address | IPv6Address | None = None,
        src: IPv4Address | IPv6Address | None = None,
        iifname: str | None = None,
        oifname: str | None = None,
        goto: int | None = None,
        fwmark: int | None = None,
        flow: int | None = None,
        fwmask: int | None = None,
        l3mdev: bool | None = None,
        suppress_prefixlen: int | None = None,
    ) -> RuleMessage:
        """
        Build a base RuleMessage for adding a routing rule.
        """
        rule = RuleMessage()
        
        rule.rtm_family = family
        rule.rtm_action = action
        
        if table is not None:
            rule.rtm_table = table

        # Add destination prefix
        if dst is not None:
            if isinstance(dst, IPv4Address):
                rule.rtm_dst_len = 32
            else:
                rule.rtm_dst_len = 128
            rule.add_attribute(RuleAttributeType.FRA_DST, dst)

        # Add source prefix
        if src is not None:
            if isinstance(src, IPv4Address):
                rule.rtm_src_len = 32
            else:
                rule.rtm_src_len = 128
            rule.add_attribute(RuleAttributeType.FRA_SRC, src)

        # Add priority
        if priority is not None:
            rule.add_attribute(RuleAttributeType.FRA_PRIORITY, priority)

        # Add input interface name
        if iifname is not None:
            rule.add_attribute(RuleAttributeType.FRA_IIFNAME, iifname)

        # Add output interface name
        if oifname is not None:
            rule.add_attribute(RuleAttributeType.FRA_OIFNAME, oifname)

        # Add goto rule
        if goto is not None:
            rule.add_attribute(RuleAttributeType.FRA_GOTO, goto)

        # Add fwmark
        if fwmark is not None:
            rule.add_attribute(RuleAttributeType.FRA_FWMARK, fwmark)

        # Add flow
        if flow is not None:
            rule.add_attribute(RuleAttributeType.FRA_FLOW, flow)

        # Add fwmask
        if fwmask is not None:
            rule.add_attribute(RuleAttributeType.FRA_FWMASK, fwmask)

        # Add l3mdev
        if l3mdev is not None:
            rule.add_attribute(RuleAttributeType.FRA_L3MDEV, 1 if l3mdev else 0)

        # Add suppress_prefixlen
        if suppress_prefixlen is not None:
            rule.add_attribute(RuleAttributeType.FRA_SUPPRESS_PREFIXLEN, suppress_prefixlen)

        return rule

    async def _send_add_msg(self, rule: RuleMessage, replace: bool = False) -> None:
        flags = (
            NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK
        )
        if replace:
            flags |= NetlinkMessageFlags.NLM_F_REPLACE
        else:
            flags |= NetlinkMessageFlags.NLM_F_CREATE | NetlinkMessageFlags.NLM_F_EXCL

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_NEWRULE,
            nlmsg_flags=flags,
            payload=rule,
        )
        await self.socket.request(msg)

    async def add(
        self,
        family: AddressFamily,
        table: int,
        priority: int,
        action: RuleAction = RuleAction.FR_ACT_TO_TBL,
        dst: IPv4Address | IPv6Address | None = None,
        src: IPv4Address | IPv6Address | None = None,
        iifname: str | None = None,
        oifname: str | None = None,
        goto: int | None = None,
        fwmark: int | None = None,
        flow: int | None = None,
        fwmask: int | None = None,
        l3mdev: bool | None = None,
        suppress_prefixlen: int | None = None,
    ) -> None:
        """
        Add a routing rule.
        
        Args:
            family: Address family (AF_INET or AF_INET6)
            table: Table ID to route to
            priority: Rule priority (lower = higher priority)
            action: Rule action (default: FR_ACT_TO_TBL)
            dst: Destination prefix to match
            src: Source prefix to match
            iifname: Input interface name to match
            oifname: Output interface name to match
            goto: Rule to jump to
            fwmark: Firewall mark to match
            flow: Flow ID
            fwmask: Firewall mark mask
            l3mdev: Match L3 master device
            suppress_prefixlen: Suppress routing lookups with prefix length
        """
        rule = self._base_add_msg(
            family=family,
            table=table,
            action=action,
            priority=priority,
            dst=dst,
            src=src,
            iifname=iifname,
            oifname=oifname,
            goto=goto,
            fwmark=fwmark,
            flow=flow,
            fwmask=fwmask,
            l3mdev=l3mdev,
            suppress_prefixlen=suppress_prefixlen,
        )

        await self._send_add_msg(rule)

    async def add_ipv4(
        self,
        table: int,
        priority: int,
        **kwargs,
    ) -> None:
        """
        Add an IPv4 routing rule.
        
        Args:
            table: Table ID to route to
            priority: Rule priority
            **kwargs: Additional arguments passed to add()
        """
        await self.add(
            family=AddressFamily.AF_INET,
            table=table,
            priority=priority,
            **kwargs,
        )

    async def add_ipv6(
        self,
        table: int,
        priority: int,
        **kwargs,
    ) -> None:
        """
        Add an IPv6 routing rule.
        
        Args:
            table: Table ID to route to
            priority: Rule priority
            **kwargs: Additional arguments passed to add()
        """
        await self.add(
            family=AddressFamily.AF_INET6,
            table=table,
            priority=priority,
            **kwargs,
        )

    async def add_lookup(
        self,
        table: int,
        priority: int,
        family: AddressFamily = AddressFamily.AF_INET,
        **kwargs,
    ) -> None:
        """
        Add a rule to lookup a routing table.
        
        Args:
            table: Table ID to lookup
            priority: Rule priority
            family: Address family
            **kwargs: Additional match criteria
        """
        await self.add(
            family=family,
            table=table,
            priority=priority,
            action=RuleAction.FR_ACT_TO_TBL,
            **kwargs,
        )

    async def add_goto(
        self,
        goto: int,
        priority: int,
        family: AddressFamily = AddressFamily.AF_INET,
        **kwargs,
    ) -> None:
        """
        Add a rule to jump to another rule.
        
        Args:
            goto: Priority of rule to jump to
            priority: This rule's priority
            family: Address family
            **kwargs: Additional match criteria
        """
        await self.add(
            family=family,
            table=0,
            priority=priority,
            action=RuleAction.FR_ACT_GOTO,
            goto=goto,
            **kwargs,
        )

    async def add_nop(
        self,
        priority: int,
        family: AddressFamily = AddressFamily.AF_INET,
        **kwargs,
    ) -> None:
        """
        Add a NOP rule (no-op, used as placeholder).
        
        Args:
            priority: Rule priority
            family: Address family
            **kwargs: Additional match criteria
        """
        await self.add(
            family=family,
            table=0,
            priority=priority,
            action=RuleAction.FR_ACT_NOP,
            **kwargs,
        )

    async def add_blackhole(
        self,
        priority: int,
        family: AddressFamily = AddressFamily.AF_INET,
        **kwargs,
    ) -> None:
        """
        Add a blackhole rule (silently drop packets).
        
        Args:
            priority: Rule priority
            family: Address family
            **kwargs: Additional match criteria
        """
        await self.add(
            family=family,
            table=0,
            priority=priority,
            action=RuleAction.FR_ACT_BLACKHOLE,
            **kwargs,
        )

    async def add_unreachable(
        self,
        priority: int,
        family: AddressFamily = AddressFamily.AF_INET,
        **kwargs,
    ) -> None:
        """
        Add an unreachable rule (send ICMP unreachable).
        
        Args:
            priority: Rule priority
            family: Address family
            **kwargs: Additional match criteria
        """
        await self.add(
            family=family,
            table=0,
            priority=priority,
            action=RuleAction.FR_ACT_UNREACHABLE,
            **kwargs,
        )

    async def add_prohibit(
        self,
        priority: int,
        family: AddressFamily = AddressFamily.AF_INET,
        **kwargs,
    ) -> None:
        """
        Add a prohibit rule (send ICMP administratively prohibited).
        
        Args:
            priority: Rule priority
            family: Address family
            **kwargs: Additional match criteria
        """
        await self.add(
            family=family,
            table=0,
            priority=priority,
            action=RuleAction.FR_ACT_PROHIBIT,
            **kwargs,
        )

    async def delete(
        self,
        family: AddressFamily,
        priority: int | None = None,
        dst: IPv4Address | IPv6Address | None = None,
        src: IPv4Address | IPv6Address | None = None,
        iifname: str | None = None,
        fwmark: int | None = None,
        table: int | None = None,
    ) -> None:
        """
        Delete a routing rule.
        
        Args:
            family: Address family
            priority: Rule priority (optional, helps identify rule)
            dst: Destination prefix
            src: Source prefix
            iifname: Input interface name
            fwmark: Firewall mark
            table: Table ID
        """
        rule = RuleMessage()
        rule.rtm_family = family
        rule.rtm_action = RuleAction.FR_ACT_TO_TBL

        if priority is not None:
            rule.add_attribute(RuleAttributeType.FRA_PRIORITY, priority)

        if dst is not None:
            if isinstance(dst, IPv4Address):
                rule.rtm_dst_len = 32
            else:
                rule.rtm_dst_len = 128
            rule.add_attribute(RuleAttributeType.FRA_DST, dst)

        if src is not None:
            if isinstance(src, IPv4Address):
                rule.rtm_src_len = 32
            else:
                rule.rtm_src_len = 128
            rule.add_attribute(RuleAttributeType.FRA_SRC, src)

        if iifname is not None:
            rule.add_attribute(RuleAttributeType.FRA_IIFNAME, iifname)

        if fwmark is not None:
            rule.add_attribute(RuleAttributeType.FRA_FWMARK, fwmark)

        if table is not None:
            rule.rtm_table = table

        msg = NetlinkMessage(
            nlmsg_type=NetlinkMessageType.RTM_DELRULE,
            nlmsg_flags=NetlinkMessageFlags.NLM_F_REQUEST
            | NetlinkMessageFlags.NLM_F_ACK,
            payload=rule,
        )

        await self.socket.request(msg)

    async def delete_ipv4(
        self,
        **kwargs,
    ) -> None:
        """
        Delete an IPv4 routing rule.
        
        Args:
            **kwargs: Arguments passed to delete()
        """
        await self.delete(family=AddressFamily.AF_INET, **kwargs)

    async def delete_ipv6(
        self,
        **kwargs,
    ) -> None:
        """
        Delete an IPv6 routing rule.
        
        Args:
            **kwargs: Arguments passed to delete()
        """
        await self.delete(family=AddressFamily.AF_INET6, **kwargs)
