import pytest

from routesia.cli.types import (
    Int8,
    Int16,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
)


def test_int8():
    assert Int8(0) == 0
    assert Int8(-128) == -128
    assert Int8(127) == 127

    with pytest.raises(ValueError) as excinfo:
        Int8(-129)
    assert str(excinfo.value) == "must be between -128 and 127 inclusive"

    with pytest.raises(ValueError) as excinfo:
        Int8(128)
    assert str(excinfo.value) == "must be between -128 and 127 inclusive"


def test_int16():
    assert Int16(0) == 0
    assert Int16(-32768) == -32768
    assert Int16(32767) == 32767

    with pytest.raises(ValueError) as excinfo:
        Int16(-32769)
    assert str(excinfo.value) == "must be between -32768 and 32767 inclusive"

    with pytest.raises(ValueError) as excinfo:
        Int16(32768)
    assert str(excinfo.value) == "must be between -32768 and 32767 inclusive"


def test_int32():
    assert Int32(0) == 0
    assert Int32(-2147483648) == -2147483648
    assert Int32(2147483647) == 2147483647

    with pytest.raises(ValueError) as excinfo:
        Int32(-2147483649)
    assert str(excinfo.value) == "must be between -2147483648 and 2147483647 inclusive"

    with pytest.raises(ValueError) as excinfo:
        Int32(2147483648)
    assert str(excinfo.value) == "must be between -2147483648 and 2147483647 inclusive"


def test_int64():
    assert Int64(0) == 0
    assert Int64(-9223372036854775808) == -9223372036854775808
    assert Int64(9223372036854775807) == 9223372036854775807

    with pytest.raises(ValueError) as excinfo:
        Int64(-9223372036854775809)
    assert str(excinfo.value) == "must be between -9223372036854775808 and 9223372036854775807 inclusive"

    with pytest.raises(ValueError) as excinfo:
        Int64(9223372036854775808)
    assert str(excinfo.value) == "must be between -9223372036854775808 and 9223372036854775807 inclusive"


def test_uint8():
    assert UInt8(0) == 0
    assert UInt8(255) == 255

    with pytest.raises(ValueError) as excinfo:
        UInt8(-1)
    assert str(excinfo.value) == "must be between 0 and 255 inclusive"

    with pytest.raises(ValueError) as excinfo:
        UInt8(256)
    assert str(excinfo.value) == "must be between 0 and 255 inclusive"


def test_uint16():
    assert UInt16(0) == 0
    assert UInt16(65535) == 65535

    with pytest.raises(ValueError) as excinfo:
        UInt16(-1)
    assert str(excinfo.value) == "must be between 0 and 65535 inclusive"

    with pytest.raises(ValueError) as excinfo:
        UInt16(65536)
    assert str(excinfo.value) == "must be between 0 and 65535 inclusive"


def test_uint32():
    assert UInt32(0) == 0
    assert UInt32(4294967295) == 4294967295

    with pytest.raises(ValueError) as excinfo:
        UInt32(-1)
    assert str(excinfo.value) == "must be between 0 and 4294967295 inclusive"

    with pytest.raises(ValueError) as excinfo:
        UInt32(4294967296)
    assert str(excinfo.value) == "must be between 0 and 4294967295 inclusive"


def test_uint64():
    assert UInt64(0) == 0
    assert UInt64(18446744073709551615) == 18446744073709551615

    with pytest.raises(ValueError) as excinfo:
        UInt64(-1)
    assert str(excinfo.value) == "must be between 0 and 18446744073709551615 inclusive"

    with pytest.raises(ValueError) as excinfo:
        UInt64(18446744073709551616)
    assert str(excinfo.value) == "must be between 0 and 18446744073709551615 inclusive"
