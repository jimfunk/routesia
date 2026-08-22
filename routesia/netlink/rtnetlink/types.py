"""
rtnetlink type definitions.

Common type annotations used across rtnetlink modules.
"""

from typing import Annotated

from routesia.interface.eui import EUI
from routesia.protoclass import FixedLengthData


# EUI type for 6-byte addresses (MAC addresses)
EUI6 = Annotated[EUI, FixedLengthData(6, to_python=EUI, from_python=bytes)]


# EUI type for 8-byte addresses (EUI-64)
EUI8 = Annotated[EUI, FixedLengthData(8, to_python=EUI, from_python=bytes)]


# Union supporting both 6 and 8 byte EUI addresses
EUI = EUI6 | EUI8
