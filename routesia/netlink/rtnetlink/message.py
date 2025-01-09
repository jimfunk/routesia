from ctypes import Structure, sizeof
from inspect import isclass
from ipaddress import (
    IPv4Address,
    IPv6Address,
)
from types import UnionType
from typing import Iterable, Type

from routesia.netlink import constants
from routesia.netlink.exceptions import NetlinkMessageException
from routesia.netlink.rtnetlink.attribute import (
    RTAttribute,
    rta_align,
)
from routesia.netlink.types import FixedWidthInt


class RTNetlinkMessage(Structure):
    """
    Base class for all rtnetlink messages
    """

    _rtattr_type_map: dict[
        int,
        Type[
            FixedWidthInt
            | bytes
            | str
            | Structure
            | IPv4Address
            | IPv6Address
            | UnionType
        ],
    ] = {}

    def __init__(self):
        super().__init__()
        self.attributes = {}

    def __bytes__(self) -> bytes:
        return bytes(memoryview(self)) + b"".join(
            [bytes(attr) for     attr in self._iter_attributes()]
        )

    def __len__(self) -> int:
        return sizeof(self)

    def _iter_attributes(self) -> Iterable[RTAttribute]:
        """
        Return an iterator of attribute values
        """
        for rta_type, values in self.attributes.items():
            for value in values:
                if not isinstance(value, bytes):
                    if isinstance(value, str):
                        value = value.encode()
                    elif isinstance(value, (IPv4Address, IPv6Address)):
                        value = value.packed
                    else:
                        value = bytes(value)
                yield RTAttribute(rta_type, value)

    def add_attribute(
        self,
        type: int,
        value: (
            FixedWidthInt
            | bytes
            | str
            | Structure
            | IPv4Address
            | IPv6Address
            | UnionType
        ),
    ):
        """
        Add an attribute to the message
        """
        if type not in self.attributes:
            self.attributes[type] = []
        self.attributes[type].append(value)

    @classmethod
    def from_buffer(cls, buf: bytes, offset: int = 0) -> "RTNetlinkMessage":
        rtmsg = type(Structure).from_buffer(cls, buf, offset)
        rtmsg.attributes = {}

        idx = offset + sizeof(cls)

        while idx < len(buf):
            if len(buf) - idx < sizeof(RTAttribute):
                break
            header = RTAttribute.from_buffer(buf[idx:])
            if header.rta_len < sizeof(RTAttribute) or header.rta_len > len(buf) - idx:
                raise NetlinkMessageException(
                    f"Invalid attribute length for attribute: {header.rta_type}, length: {header.rta_len}"
                )
            attr_type = cls._rtattr_type_map.get(header.rta_type, bytes)
            data = buf[idx + sizeof(header): idx + header.rta_len]
            if isclass(attr_type) and issubclass(attr_type, Structure):
                value = attr_type.from_buffer(data)
            else:
                value = cls._parse_attribute(attr_type, data)

            rtmsg.add_attribute(header.rta_type, value)
            idx += rta_align(header.rta_len)

        return rtmsg

    @classmethod
    def from_buffer_copy(cls, buf: bytes, offset: int = 0) -> "RTNetlinkMessage":
        rtmsg = type(Structure).from_buffer_copy(cls, buf, offset)
        rtmsg.attributes = {}

        idx = offset + sizeof(cls)

        while idx < len(buf):
            if len(buf) - idx < sizeof(RTAttribute):
                break
            header = RTAttribute.from_buffer(buf[idx:])
            if header.rta_len < sizeof(RTAttribute) or header.rta_len > len(buf) - idx:
                raise NetlinkMessageException(
                    f"Invalid attribute length for attribute: {header.rta_type}, length: {header.rta_len}"
                )
            attr_type = cls._rtattr_type_map.get(header.rta_type, bytes)
            data = buf[idx + sizeof(header): idx + header.rta_len]
            if isclass(attr_type) and issubclass(attr_type, Structure):
                value = attr_type.from_buffer_copy(data)
            else:
                value = cls._parse_attribute(attr_type, data)

            rtmsg.add_attribute(header.rta_type, value)
            idx += rta_align(header.rta_len)

        return rtmsg

    @classmethod
    def _parse_attribute(cls, attr_type: int, attr_data: bytes):
        """
        Parse an attribute according to a type definition and return the value.
        """
        if attr_type == bytes:
            return attr_data

        if isinstance(attr_type, UnionType):
            for subtype in attr_type.__args__:
                try:
                    return cls._parse_attribute(subtype, attr_data)
                except ValueError:
                    raise
            raise ValueError("No given type matched the attribute data")
        elif issubclass(attr_type, FixedWidthInt):
            return attr_type.from_bytes(attr_data)
        elif attr_type in (IPv4Address, IPv6Address):
            return attr_type(bytes(attr_data))

        return attr_data
