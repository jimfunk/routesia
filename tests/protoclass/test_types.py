import pytest
import sys
from typing import Annotated

from routesia.protoclass import protoclass, ProtoClass
from routesia.protoclass.types import (
    Int8,
    Int16,
    Int32,
    Int64,
    Int128,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    UInt128,
    FixedLengthData,
    VariableLengthData,
)


def create_type_container(type_hint, byteorder="native"):
    @protoclass(byteorder=byteorder)
    class TypeContainer(ProtoClass):
        val: type_hint

    return TypeContainer


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", -128),
        (b"\xff", -1),
    ),
)
def test_int8(data, value):
    cls = create_type_container(Int8)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", 128),
        (b"\xff", 255),
    ),
)
def test_uint8(data, value):
    cls = create_type_container(UInt8)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


# --- Little Endian Explicit Tests ---


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00", 0),
        (b"\x01\x00", 1),
        (b"\xff\x7f", 32767),
        (b"\x00\x80", -32768),
        (b"\xff\xff", -1),
    ),
)
def test_int16_little(data, value):
    cls = create_type_container(Int16, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00", 0),
        (b"\x01\x00", 1),
        (b"\xff\x7f", 32767),
        (b"\x00\x80", 32768),
        (b"\xff\xff", 65535),
    ),
)
def test_uint16_little(data, value):
    cls = create_type_container(UInt16, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00", 0),
        (b"\x01\x00\x00\x00", 1),
        (b"\xff\xff\xff\x7f", 2147483647),
        (b"\x00\x00\x00\x80", -2147483648),
        (b"\xff\xff\xff\xff", -1),
    ),
)
def test_int32_little(data, value):
    cls = create_type_container(Int32, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00", 0),
        (b"\x01\x00\x00\x00", 1),
        (b"\xff\xff\xff\x7f", 2147483647),
        (b"\x00\x00\x00\x80", 2147483648),
        (b"\xff\xff\xff\xff", 4294967295),
    ),
)
def test_uint32_little(data, value):
    cls = create_type_container(UInt32, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
        (b"\x01\x00\x00\x00\x00\x00\x00\x00", 1),
        (b"\xff\xff\xff\xff\xff\xff\xff\x7f", 9223372036854775807),
        (b"\x00\x00\x00\x00\x00\x00\x00\x80", -9223372036854775808),
        (b"\xff\xff\xff\xff\xff\xff\xff\xff", -1),
    ),
)
def test_int64_little(data, value):
    cls = create_type_container(Int64, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
        (b"\x01\x00\x00\x00\x00\x00\x00\x00", 1),
        (b"\xff\xff\xff\xff\xff\xff\xff\x7f", 9223372036854775807),
        (b"\x00\x00\x00\x00\x00\x00\x00\x80", 9223372036854775808),
        (b"\xff\xff\xff\xff\xff\xff\xff\xff", 18446744073709551615),
    ),
)
def test_uint64_little(data, value):
    cls = create_type_container(UInt64, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00" * 16, 0),
        (b"\x01" + b"\x00" * 15, 1),
        (b"\xff" * 15 + b"\x7f", (1 << 127) - 1),
        (b"\x00" * 15 + b"\x80", -(1 << 127)),
        (b"\xff" * 16, -1),
    ),
)
def test_int128_little(data, value):
    cls = create_type_container(Int128, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00" * 16, 0),
        (b"\x01" + b"\x00" * 15, 1),
        (b"\xff" * 15 + b"\x7f", (1 << 127) - 1),
        (b"\x00" * 15 + b"\x80", 1 << 127),
        (b"\xff" * 16, (1 << 128) - 1),
    ),
)
def test_uint128_little(data, value):
    cls = create_type_container(UInt128, "little")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


# --- Big Endian Explicit Tests ---


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00", 0),
        (b"\x00\x01", 1),
        (b"\x7f\xff", 32767),
        (b"\x80\x00", -32768),
        (b"\xff\xff", -1),
    ),
)
def test_int16_big(data, value):
    cls = create_type_container(Int16, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00", 0),
        (b"\x00\x01", 1),
        (b"\x7f\xff", 32767),
        (b"\x80\x00", 32768),
        (b"\xff\xff", 65535),
    ),
)
def test_uint16_big(data, value):
    cls = create_type_container(UInt16, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00", 0),
        (b"\x00\x00\x00\x01", 1),
        (b"\x7f\xff\xff\xff", 2147483647),
        (b"\x80\x00\x00\x00", -2147483648),
        (b"\xff\xff\xff\xff", -1),
    ),
)
def test_int32_big(data, value):
    cls = create_type_container(Int32, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00", 0),
        (b"\x00\x00\x00\x01", 1),
        (b"\x7f\xff\xff\xff", 2147483647),
        (b"\x80\x00\x00\x00", 2147483648),
        (b"\xff\xff\xff\xff", 4294967295),
    ),
)
def test_uint32_big(data, value):
    cls = create_type_container(UInt32, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
        (b"\x00\x00\x00\x00\x00\x00\x00\x01", 1),
        (b"\x7f\xff\xff\xff\xff\xff\xff\xff", 9223372036854775807),
        (b"\x80\x00\x00\x00\x00\x00\x00\x00", -9223372036854775808),
        (b"\xff\xff\xff\xff\xff\xff\xff\xff", -1),
    ),
)
def test_int64_big(data, value):
    cls = create_type_container(Int64, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
        (b"\x00\x00\x00\x00\x00\x00\x00\x01", 1),
        (b"\x7f\xff\xff\xff\xff\xff\xff\xff", 9223372036854775807),
        (b"\x80\x00\x00\x00\x00\x00\x00\x00", 9223372036854775808),
        (b"\xff\xff\xff\xff\xff\xff\xff\xff", 18446744073709551615),
    ),
)
def test_uint64_big(data, value):
    cls = create_type_container(UInt64, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00" * 16, 0),
        (b"\x00" * 15 + b"\x01", 1),
        (b"\x7f" + b"\xff" * 15, (1 << 127) - 1),
        (b"\x80" + b"\x00" * 15, -(1 << 127)),
        (b"\xff" * 16, -1),
    ),
)
def test_int128_big(data, value):
    cls = create_type_container(Int128, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00" * 16, 0),
        (b"\x00" * 15 + b"\x01", 1),
        (b"\x7f" + b"\xff" * 15, (1 << 127) - 1),
        (b"\x80" + b"\x00" * 15, 1 << 127),
        (b"\xff" * 16, (1 << 128) - 1),
    ),
)
def test_uint128_big(data, value):
    cls = create_type_container(UInt128, "big")
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


# --- Native Endian Explicit Tests ---


@pytest.mark.parametrize(
    "data, value",
    [(v.to_bytes(2, sys.byteorder, signed=True), v) for v in (0, 1, 32767, -32768, -1)],
)
def test_int16_native(data, value):
    cls = create_type_container(Int16)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(2, sys.byteorder, signed=False), v)
        for v in (0, 1, 32767, 32768, 65535)
    ],
)
def test_uint16_native(data, value):
    cls = create_type_container(UInt16)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(4, sys.byteorder, signed=True), v)
        for v in (0, 1, 2147483647, -2147483648, -1)
    ],
)
def test_int32_native(data, value):
    cls = create_type_container(Int32)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(4, sys.byteorder, signed=False), v)
        for v in (0, 1, 2147483647, 2147483648, 4294967295)
    ],
)
def test_uint32_native(data, value):
    cls = create_type_container(UInt32)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(8, sys.byteorder, signed=True), v)
        for v in (0, 1, 9223372036854775807, -9223372036854775808, -1)
    ],
)
def test_int64_native(data, value):
    cls = create_type_container(Int64)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(8, sys.byteorder, signed=False), v)
        for v in (0, 1, 9223372036854775807, 9223372036854775808, 18446744073709551615)
    ],
)
def test_uint64_native(data, value):
    cls = create_type_container(UInt64)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(16, sys.byteorder, signed=True), v)
        for v in (0, 1, (1 << 127) - 1, -(1 << 127), -1)
    ],
)
def test_int128_native(data, value):
    cls = create_type_container(Int128)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


@pytest.mark.parametrize(
    "data, value",
    [
        (v.to_bytes(16, sys.byteorder, signed=False), v)
        for v in (0, 1, (1 << 127) - 1, 1 << 127, (1 << 128) - 1)
    ],
)
def test_uint128_native(data, value):
    cls = create_type_container(UInt128)
    assert cls.from_bytes(data).val == value
    assert bytes(cls(val=value)) == data


# --- Data conversion tests ---


def test_fixed_length_bytes():
    @protoclass()
    class FixedBytes(ProtoClass):
        val: Annotated[bytes, FixedLengthData(4)]

    obj = FixedBytes.from_bytes(b"1234")
    assert obj.val == b"1234"
    assert bytes(obj) == b"1234"


def test_fixed_length_bytes_conversion():
    @protoclass()
    class FixedString(ProtoClass):
        val: Annotated[
            str,
            FixedLengthData(
                4, to_python=lambda x: x.decode(), from_python=lambda x: x.encode()
            ),
        ]

    obj = FixedString.from_bytes(b"1234")
    assert obj.val == "1234"
    assert bytes(obj) == b"1234"


def test_variable_length_bytes():
    @protoclass()
    class VarBytes(ProtoClass):
        val: Annotated[bytes, VariableLengthData()]

    obj = VarBytes.from_bytes(b"123456")
    assert obj.val == b"123456"
    assert bytes(obj) == b"123456"


def test_variable_length_bytes_conversion():
    @protoclass()
    class VarString(ProtoClass):
        val: Annotated[
            str,
            VariableLengthData(
                to_python=lambda x: x.decode(), from_python=lambda x: x.encode()
            ),
        ]

    obj = VarString.from_bytes(b"hello world")
    assert obj.val == "hello world"
    assert bytes(obj) == b"hello world"
