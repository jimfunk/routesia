"""
Types used in attributes
"""
from ipaddress import IPv4Address, IPv6Address, ip_address
import sys


class FixedWidthIntMeta(type):
    def __new__(cls, name, bases, attrs):
        if name == "FixedWidthInt":
            return super().__new__(cls, name, bases, attrs)

        bits = attrs.get("_bits", 0)
        signed = attrs.get("_signed", False)

        if bits <= 0:
            raise ValueError(f"Class {name} must define _bits")

        mask = (1 << bits) - 1
        max_val = (1 << (bits - 1)) - 1 if signed else mask

        attrs["_mask"] = mask
        attrs["_max"] = max_val

        return super().__new__(cls, name, bases, attrs)


class FixedWidthInt(int, metaclass=FixedWidthIntMeta):
    _bits: int = 0
    _signed: bool = False

    def __new__(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, int):
            raise TypeError(f"Invalid value {value} for {cls.__name__}")

        mask = cls._mask
        max_val = cls._max

        normalized = value & mask

        if cls._signed and normalized > max_val:
            normalized -= 1 << cls._bits

        return super().__new__(cls, normalized)

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == other
        if isinstance(other, FixedWidthInt):
            return int(self) == int(other)
        return super().__eq__(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({int(self)})"

    def __str__(self):
        return str(int(self))

    def __bytes__(self):
        print(self._bits // 8)
        return self.to_bytes(self._bits // 8, byteorder=sys.byteorder, signed=self._signed)

    @classmethod
    def from_bytes(cls, bytes_: bytes | bytearray | memoryview):  # type: ignore
        """
        Deserialize from bytes using system byte order.

        Args:
            bytes_ (bytes): Input bytes to convert

        Returns:
            cls: New instance of the type
        """
        if not isinstance(bytes_, (bytes, bytearray, memoryview)):
            raise TypeError("from_bytes() argument must be bytes")

        value = int.from_bytes(bytes_, byteorder=sys.byteorder, signed=cls._signed)
        return cls(value)


class UInt8(FixedWidthInt):
    _bits = 8
    _signed = False


class UInt16(FixedWidthInt):
    _bits = 16
    _signed = False


class UInt32(FixedWidthInt):
    _bits = 32
    _signed = False


class UInt64(FixedWidthInt):
    _bits = 64
    _signed = False


class Int8(FixedWidthInt):
    _bits = 8
    _signed = True


class Int16(FixedWidthInt):
    _bits = 16
    _signed = True


class Int32(FixedWidthInt):
    _bits = 32
    _signed = True


class Int64(FixedWidthInt):
    _bits = 64
    _signed = True
