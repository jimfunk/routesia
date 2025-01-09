from ctypes import (
    POINTER,
    Structure,
    addressof,
    c_uint16,
    cast,
    sizeof,
)
from typing import Iterator

from routesia.netlink.message import (
    NetlinkMessage,
    NetlinkMessageException,
)


def rta_align(length: int) -> int:
    """
    Get the space required for length after alignment
    """
    return (length + 3) & ~3


def rta_length(payload_len: int) -> int:
    """
    Get the length of payload plus header
    """
    return payload_len + sizeof(RTAttribute)


def rta_space(payload_len: int) -> int:
    """
    Get the full space required for payload plus header after alignment
    """
    return rta_align(rta_length(payload_len))


class RTAttribute(Structure):
    _fields_ = [
        ("rta_len", c_uint16),
        ("rta_type", c_uint16),
    ]
    rta_len: int
    rta_type: int


class RTNetlinkMessage(NetlinkMessage):
    @property
    def attributes(self) -> Iterator[RTAttribute]:
        """
        Returns an iterator of the message attributes
        """
        header_len = sizeof(self.__class__)
        attr_start = addressof(self) + header_len
        total_attr_len = self.nlmsg_len - header_len

        idx = 0

        while idx < total_attr_len:
            if total_attr_len - idx < sizeof(RTAttribute):
                # No more space for attribute header
                break
            attr = cast(attr_start + idx, POINTER(RTAttribute))[0]
            if (
                attr.rta_len < sizeof(RTAttribute)
                or attr.rta_len > total_attr_len - idx
            ):
                raise NetlinkMessageException(
                    f"Invalid attribute length for attribute: {attr.rta_type}, length: {attr.rta_len}"
                )

            yield attr

            idx += rta_align(attr.rta_len)
