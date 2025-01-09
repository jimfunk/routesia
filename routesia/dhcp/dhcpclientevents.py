"""
DHCPv4 client events.
"""

from dataclasses import dataclass
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
)

from routesia.event import Event


@dataclass
class DHCPv4Route:
    destination: IPv4Network
    gateway: IPv4Address


@dataclass
class DHCPv4LeasePreinit(Event):
    interface: str
    table: int
    address: IPv4Interface


@dataclass
class DHCPv4LeaseAcquired(Event):
    interface: str
    table: int
    address: IPv4Interface
    gateway: IPv4Address
    routes: list[DHCPv4Route]
    mtu: int
    domain_name: str
    domain_name_servers: list[IPv4Address]
    search_domains: list[str]
    ntp_servers: list[IPv4Address]
    server_identifier: IPv4Address


@dataclass
class DHCPv4LeaseLost(Event):
    interface: str
    table: int
    address: IPv4Interface
    gateway: IPv4Address | None
    routes: list[DHCPv4Route]
    mtu: int
    domain_name: str
    domain_name_servers: list[IPv4Address]
    search_domains: list[str]
    ntp_servers: list[IPv4Address]
    server_identifier: IPv4Address
