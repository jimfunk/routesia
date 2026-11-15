"""
routesia/interface/events.py - Interface events
"""

from dataclasses import dataclass

from routesia.event import Event


@dataclass
class PPPoELinkUp(Event):
    """
    A PPPoE session has negotiating addressing for an address family
    """

    interface: str
    table: int
    family: int


@dataclass
class PPPoELinkDown(Event):
    """
    A PPPoE session has lost all addressing for an address family
    """

    interface: str
    table: int
    family: int
