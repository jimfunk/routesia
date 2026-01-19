import pytest

from routesia.netlink.rtnetlink.attribute import (
    rta_align,
    rta_length,
    rta_space,
    RTAttribute,
)

from tests.buffers import HexBuffer


@pytest.mark.parametrize(
    "value, expected",
    (
        (1, 4),
        (3, 4),
        (4, 4),
        (5, 8),
    ),
)
def test_rta_align(value, expected):
    assert rta_align(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (1, 5),
        (3, 7),
        (4, 8),
        (5, 9),
        (8, 12),
    ),
)
def test_rta_length(value, expected):
    assert rta_length(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (1, 8),
        (3, 8),
        (4, 8),
        (5, 12),
        (8, 12),
    ),
)
def test_rta_space(value, expected):
    assert rta_space(value) == expected


@pytest.mark.parametrize(
    "input, rta_len, rta_type, payload",
    (
        ("08 00 0F 00 FE 00 00 00", 8, 15, b"\xfe\x00\x00\x00"),
        ("05 00 14 00 10 00 00 00", 5, 20, b"\x10"),
        ("08 00 04 00 02 00 00 00", 8, 4, b"\x02\x00\x00\x00"),
    ),
)
def test_attribute_from_buffer(input, rta_len, rta_type, payload):
    buf = HexBuffer(input)
    attr = RTAttribute.from_buffer(buf)
    assert attr.rta_len == rta_len
    assert attr.rta_type == rta_type
    assert attr.payload == payload


@pytest.mark.parametrize(
    "input, rta_len, rta_type, payload",
    (
        ("08 00 0F 00 FE 00 00 00", 8, 15, b"\xfe\x00\x00\x00"),
        ("05 00 14 00 10 00 00 00", 5, 20, b"\x10"),
        ("08 00 04 00 02 00 00 00", 8, 4, b"\x02\x00\x00\x00"),
    ),
)
def test_attribute_from_buffer_copy(input, rta_len, rta_type, payload):
    buf = HexBuffer(input)
    attr = RTAttribute.from_buffer(buf)
    assert attr.rta_len == rta_len
    assert attr.rta_type == rta_type
    assert attr.payload == payload


@pytest.mark.parametrize(
    "rta_type, payload, output",
    (
        (15, b"\xfe\x00\x00\x00", "08 00 0F 00 FE 00 00 00"),
        (20, b"\x10", "05 00 14 00 10 00 00 00"),
        (4, b"\x02\x00\x00\x00", "08 00 04 00 02 00 00 00"),
    ),
)
def test_attribute_as_bytes(rta_type, payload, output):
    attr = RTAttribute(rta_type=rta_type, payload=payload)
    assert bytes(attr) == HexBuffer(output)
