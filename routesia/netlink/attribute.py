from __future__ import annotations
from typing import Annotated

from routesia.protoclass import protoclass, UInt16, VariableLengthData


@protoclass()
class NlAttr:
    """
    Netlink attribute structure
    """

    nla_len: UInt16
    nla_type: UInt16
    payload: Annotated[
        bytes,
        VariableLengthData(
            length_field="nla_len",
            length_offset=-4,  # subtract header size to get payload length
            align=4,
        ),
    ]
