from typing import Annotated
from routesia.protoclass import ProtoClass, protoclass, VariableLengthData
from routesia.protoclass.types import UInt16


@protoclass()
class RTAttribute():
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        bytes, VariableLengthData(length_field="rta_len", length_offset=-4, align=4)
    ]


def rta_align(length: int) -> int:
    return (length + 3) & ~3


def rta_length(payload_len: int) -> int:
    return payload_len + 4


def rta_space(payload_len: int) -> int:
    return rta_align(rta_length(payload_len))
