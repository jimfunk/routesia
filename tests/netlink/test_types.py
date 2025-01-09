import pytest
import sys

from routesia.netlink.types import (
    Int8,
    Int16,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
)


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", -128),
        (b"\xff", -1),
    )
)
def test_int8_from_bytes(data, value):
    assert Int8.from_bytes(data) == value


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", -128),
        (b"\xff", -1),
    )
)
def test_int8_to_bytes(data, value):
    assert bytes(Int8(value)) == data


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", 128),
        (b"\xff", 255),
    )
)
def test_uint8_from_bytes(data, value):
    assert UInt8.from_bytes(data) == value


@pytest.mark.parametrize(
    "data, value",
    (
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", 128),
        (b"\xff", 255),
    )
)
def test_uint8_to_bytes(data, value):
    assert bytes(UInt8(value)) == data


if sys.byteorder == "little":
    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x01\x00", 1),
            (b"\xff\x7f", 32767),
            (b"\x00\x80", -32768),
            (b"\xff\xff", -1),
        )
    )
    def test_int16_from_bytes(data, value):
        assert Int16.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x01\x00", 1),
            (b"\xff\x7f", 32767),
            (b"\x00\x80", -32768),
            (b"\xff\xff", -1),
        )
    )
    def test_int16_to_bytes(data, value):
        assert bytes(Int16(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x01\x00", 1),
            (b"\xff\x7f", 32767),
            (b"\x00\x80", 32768),
            (b"\xff\xff", 65535),
        )
    )
    def test_uint16_from_bytes(data, value):
        assert UInt16.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x01\x00", 1),
            (b"\xff\x7f", 32767),
            (b"\x00\x80", 32768),
            (b"\xff\xff", 65535),
        )
    )
    def test_uint16_to_bytes(data, value):
        assert bytes(UInt16(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00", 1),
            (b"\xff\xff\xff\x7f", 2147483647),
            (b"\x00\x00\x00\x80", -2147483648),
            (b"\xff\xff\xff\xff", -1),
        )
    )
    def test_int32_from_bytes(data, value):
        assert Int32.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00", 1),
            (b"\xff\xff\xff\x7f", 2147483647),
            (b"\x00\x00\x00\x80", -2147483648),
            (b"\xff\xff\xff\xff", -1),
        )
    )
    def test_int32_to_bytes(data, value):
        assert bytes(Int32(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00", 1),
            (b"\xff\xff\xff\x7f", 2147483647),
            (b"\x00\x00\x00\x80", 2147483648),
            (b"\xff\xff\xff\xff", 4294967295),
        )
    )
    def test_uint32_from_bytes(data, value):
        assert UInt32.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00", 1),
            (b"\xff\xff\xff\x7f", 2147483647),
            (b"\x00\x00\x00\x80", 2147483648),
            (b"\xff\xff\xff\xff", 4294967295),
        )
    )
    def test_uint32_to_bytes(data, value):
        assert bytes(UInt32(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00\x00\x00\x00\x00", 1),
            (b"\xff\xff\xff\xff\xff\xff\xff\x7f", 9223372036854775807),
            (b"\x00\x00\x00\x00\x00\x00\x00\x80", -9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", -1),
        )
    )
    def test_int64_from_bytes(data, value):
        assert Int64.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00\x00\x00\x00\x00", 1),
            (b"\xff\xff\xff\xff\xff\xff\xff\x7f", 9223372036854775807),
            (b"\x00\x00\x00\x00\x00\x00\x00\x80", -9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", -1),
        )
    )
    def test_int64_to_bytes(data, value):
        assert bytes(Int64(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00\x00\x00\x00\x00", 1),
            (b"\xff\xff\xff\xff\xff\xff\xff\x7f", 9223372036854775807),
            (b"\x00\x00\x00\x00\x00\x00\x00\x80", 9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", 18446744073709551615),
        )
    )
    def test_uint64_from_bytes(data, value):
        assert UInt64.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x01\x00\x00\x00\x00\x00\x00\x00", 1),
            (b"\xff\xff\xff\xff\xff\xff\xff\x7f", 9223372036854775807),
            (b"\x00\x00\x00\x00\x00\x00\x00\x80", 9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", 18446744073709551615),
        )
    )
    def test_uint64_to_bytes(data, value):
        assert bytes(UInt64(value)) == data

else:

    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x00\x01", 1),
            (b"\x7f\x7f", 32767),
            (b"\x80\x00", -32768),
            (b"\xff\xff", -1),
        )
    )
    def test_int16_from_bytes(data, value):
        assert Int16.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x00\x01", 1),
            (b"\x7f\xff", 32767),
            (b"\x80\x00", -32768),
            (b"\xff\xff", -1),
        )
    )
    def test_int16_to_bytes(data, value):
        assert bytes(Int16(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x00\x01", 1),
            (b"\x7f\x7f", 32767),
            (b"\x80\x00", 32768),
            (b"\xff\xff", 65535),
        )
    )
    def test_uint16_from_bytes(data, value):
        assert UInt16.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00", 0),
            (b"\x00\x01", 1),
            (b"\x7f\xff", 32767),
            (b"\x80\x00", 32768),
            (b"\xff\xff", 65535),
        )
    )
    def test_uint16_to_bytes(data, value):
        assert bytes(UInt16(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff", 2147483647),
            (b"\x80\x00\x00\x00", -2147483648),
            (b"\xff\xff\xff\xff", -1),
        )
    )
    def test_int32_from_bytes(data, value):
        assert Int32.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff", 2147483647),
            (b"\x80\x00\x00\x00", -2147483648),
            (b"\xff\xff\xff\xff", -1),
        )
    )
    def test_int32_to_bytes(data, value):
        assert bytes(Int32(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff", 2147483647),
            (b"\x80\x00\x00\x00", 2147483648),
            (b"\xff\xff\xff\xff", 4294967295),
        )
    )
    def test_int32_from_bytes(data, value):
        assert Int32.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff", 2147483647),
            (b"\x80\x00\x00\x00", 2147483648),
            (b"\xff\xff\xff\xff", 4294967295),
        )
    )
    def test_int32_to_bytes(data, value):
        assert bytes(Int32(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x00\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff\xff\xff\xff\xff", 9223372036854775807),
            (b"\x80\x00\x00\x00\x00\x00\x00\x00", -9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", -1),
        )
    )
    def test_int64_from_bytes(data, value):
        assert Int64.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x00\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff\xff\xff\xff\xff", 9223372036854775807),
            (b"\x80\x00\x00\x00\x00\x00\x00\x00", -9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", -1),
        )
    )
    def test_int64_to_bytes(data, value):
        assert bytes(Int64(value)) == data


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x00\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff\xff\xff\xff\xff", 9223372036854775807),
            (b"\x80\x00\x00\x00\x00\x00\x00\x00", 9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", 18446744073709551615),
        )
    )
    def test_int64_from_bytes(data, value):
        assert Int64.from_bytes(data) == value


    @pytest.mark.parametrize(
        "data, value",
        (
            (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0),
            (b"\x00\x00\x00\x00\x00\x00\x00\x01", 1),
            (b"\x7f\xff\xff\xff\xff\xff\xff\xff", 9223372036854775807),
            (b"\x80\x00\x00\x00\x00\x00\x00\x00", 9223372036854775808),
            (b"\xff\xff\xff\xff\xff\xff\xff\xff", 18446744073709551615),
        )
    )
    def test_int64_to_bytes(data, value):
        assert bytes(Int64(value)) == data
