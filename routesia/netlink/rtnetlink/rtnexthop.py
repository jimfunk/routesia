from enum import IntFlag
from typing import Annotated
from routesia.netlink import constants
from routesia.protoclass import protoclass, VariableLengthData, ProtoClass, UInt8Base
from routesia.protoclass.types import UInt, UInt16, UInt8, Int32


@protoclass()
class RTNexthopNestedAttribute(ProtoClass):
    rta_len: UInt16
    rta_type: UInt16
    payload: Annotated[
        bytes, VariableLengthData(length_field="rta_len", length_offset=-4, align=4)
    ]


class RTNexthopFlag(UInt8Base, IntFlag):
    RTNH_F_DEAD = constants.RTNH_F_DEAD
    RTNH_F_PERVASIVE = constants.RTNH_F_PERVASIVE
    RTNH_F_ONLINK = constants.RTNH_F_ONLINK
    RTNH_F_OFFLOAD = constants.RTNH_F_OFFLOAD
    RTNH_F_LINKDOWN = constants.RTNH_F_LINKDOWN
    RTNH_F_UNRESOLVED = constants.RTNH_F_UNRESOLVED
    RTNH_F_TRAP = constants.RTNH_F_TRAP


@protoclass()
class RTNexthop(ProtoClass):
    rtnh_len: UInt16
    rtnh_flags: Annotated[RTNexthopFlag, UInt8]
    rtnh_hops: UInt8
    rtnh_ifindex: Int32

    attrs: Annotated[
        list[RTNexthopNestedAttribute],
        VariableLengthData(
            length_field="rtnh_len",
            length_offset=-8,
            item_type=RTNexthopNestedAttribute,
            align=4,
        ),
    ]


@protoclass()
class RTNexthopAttribute(ProtoClass):
    nexthops: Annotated[list[RTNexthop], VariableLengthData(item_type=RTNexthop)]
