from __future__ import annotations
import ipaddress
import struct
import sys
from typing import Optional, Union, Type, Any, Annotated, Callable, get_type_hints


class Integer:
    """
    Metadata for protoclass integers.
    """

    def __init__(self, bits: int, signed: bool = False):
        self.bits = bits
        self.signed = signed

    def __repr__(self):
        return f"Integer({self.bits}, signed={self.signed})"


class VariableLengthData:
    """
    Metadata for a variable-length field or list.
    """

    __slots__ = (
        "length_field",
        "length_multiplier",
        "length_offset",
        "align",
        "type_field",
        "type_map",
        "item_type",
        "to_python",
        "from_python",
    )

    def __init__(
        self,
        *,
        length_field: Optional[str] = None,
        length_multiplier: int = 1,
        length_offset: int = 0,
        align: int = 1,
        type_field: Optional[str] = None,
        type_map: Optional[dict[Union[int, str, None], Any]] = None,
        item_type: Optional[Annotated] = None,
        to_python: Optional[Callable] = None,
        from_python: Optional[Callable] = None,
    ) -> None:
        """
        Create a new variable-length field metadata.
        """
        self.length_field = length_field
        self.length_multiplier = length_multiplier
        self.length_offset = length_offset
        self.align = align
        self.type_field = type_field
        self.type_map = type_map
        self.item_type = item_type
        self.to_python = to_python
        self.from_python = from_python

    def __repr__(self):
        return f"VariableLengthData(length_field={self.length_field!r})"


class FixedLengthData:
    """
    Metadata for a fixed-length data field.
    """

    __slots__ = (
        "length",
        "to_python",
        "from_python",
        "type_field",
        "type_map",
    )

    def __init__(
        self,
        length: int,
        *,
        to_python: Optional[Callable] = None,
        from_python: Optional[Callable] = None,
        type_field: Optional[str] = None,
        type_map: Optional[dict[Union[int, str, None], Any]] = None,
    ) -> None:
        """
        Create a new fixed-length field metadata.
        """
        self.length = length
        self.to_python = to_python
        self.from_python = from_python
        self.type_field = type_field
        self.type_map = type_map

    def __repr__(self):
        return f"FixedLengthData(length={self.length!r})"


def TypeMap(
    *,
    length_field: Optional[str] = None,
    length_multiplier: int = 1,
    length_offset: int = 0,
    align: int = 1,
    type_field: Optional[str] = None,
    type_map: Optional[dict[Union[int, str, None], Any]] = None,
    item_type: Optional[type] = None,
    length: Optional[int] = None,
) -> Any:
    """
    Helper to build an Annotated union type from a type_map.
    
    Creates a union type that dispatches to different types based on a type field.
    
    Example:
        class MyMessage:
            type: UInt8
            payload: TypeMap(
                length_field="length",
                type_field="type",
                type_map={
                    1: UInt8,
                    2: UInt16,
                    3: UInt32,
                }
            )
    """
    if type_map is None:
        type_map = {}

    types = []
    for v in type_map.values():
        if isinstance(v, (list, tuple)):
            types.append(v[0])
        else:
            types.append(v)

    if not types:
        python_type = bytes
    elif len(types) == 1:
        python_type = types[0]
    else:
        python_type = Union[tuple(types)]

    if length is not None:
        marker = FixedLengthData(
            length=length,
            type_field=type_field,
            type_map=type_map,
        )
    else:
        marker = VariableLengthData(
            length_field=length_field,
            length_multiplier=length_multiplier,
            length_offset=length_offset,
            align=align,
            type_field=type_field,
            type_map=type_map,
            item_type=item_type,
        )

    return Annotated[python_type, marker]


# Pre-defined Integer instances for common sizes
UInt1 = Annotated[int, Integer(1)]
UInt2 = Annotated[int, Integer(2)]
UInt3 = Annotated[int, Integer(3)]
UInt4 = Annotated[int, Integer(4)]
UInt5 = Annotated[int, Integer(5)]
UInt6 = Annotated[int, Integer(6)]
UInt7 = Annotated[int, Integer(7)]
UInt8 = Annotated[int, Integer(8)]
UInt9 = Annotated[int, Integer(9)]
UInt10 = Annotated[int, Integer(10)]
UInt11 = Annotated[int, Integer(11)]
UInt12 = Annotated[int, Integer(12)]
UInt13 = Annotated[int, Integer(13)]
UInt14 = Annotated[int, Integer(14)]
UInt15 = Annotated[int, Integer(15)]
UInt16 = Annotated[int, Integer(16)]
UInt20 = Annotated[int, Integer(20)]
UInt24 = Annotated[int, Integer(24)]
UInt32 = Annotated[int, Integer(32)]
UInt60 = Annotated[int, Integer(60)]
UInt64 = Annotated[int, Integer(64)]
UInt128 = Annotated[int, Integer(128)]

Int8 = Annotated[int, Integer(8, signed=True)]
Int16 = Annotated[int, Integer(16, signed=True)]
Int32 = Annotated[int, Integer(32, signed=True)]
Int64 = Annotated[int, Integer(64, signed=True)]
Int128 = Annotated[int, Integer(128, signed=True)]


# Mixin classes for enum inheritance
class UInt8Base:
    """Mixin for 8-bit enums."""

    bits = 8
    signed = False


class UInt16Base:
    """Mixin for 16-bit enums."""

    bits = 16
    signed = False


class UInt32Base:
    """Mixin for 32-bit enums."""

    bits = 32
    signed = False


class UInt64Base:
    """Mixin for 64-bit enums."""

    bits = 64
    signed = False


class UInt128Base:
    """Mixin for 128-bit enums."""

    bits = 128
    signed = False


class Int8Base:
    """Mixin for 8-bit signed enums."""

    bits = 8
    signed = True


class Int16Base:
    """Mixin for 16-bit signed enums."""

    bits = 16
    signed = True


class Int32Base:
    """Mixin for 32-bit signed enums."""

    bits = 32
    signed = True


class Int64Base:
    """Mixin for 64-bit signed enums."""

    bits = 64
    signed = True


class Int128Base:
    """Mixin for 128-bit signed enums."""

    bits = 128
    signed = True


# Marker object for null-terminated strings
NullTerminatedString = Annotated[
    str,
    VariableLengthData(
        to_python=lambda x: x.decode().split("\0")[0] if isinstance(x, bytes) else x,
        from_python=lambda x: (x.encode() + b"\0") if isinstance(x, str) else x,
    ),
]

# Standardized markers for legacy compliance
IPv4 = Annotated[
    ipaddress.IPv4Address,
    FixedLengthData(
        length=4,
        to_python=ipaddress.IPv4Address,
        from_python=lambda x: x.packed,
    ),
]
IPv6 = Annotated[
    ipaddress.IPv6Address,
    FixedLengthData(
        length=16,
        to_python=ipaddress.IPv6Address,
        from_python=lambda x: x.packed,
    ),
]
Bytes = Annotated[bytes, VariableLengthData()]

# Alias for backward compatibility during migration
VariableData = VariableLengthData
