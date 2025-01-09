import pytest

from routesia.interface.eui import EUI


@pytest.mark.parametrize(
    (
        "arg",
        "address",
    ),
    [
        ("00:01:02:A1:B2:C3", "00:01:02:a1:b2:c3"),
        ("00-01-02-A1-B2-C3", "00:01:02:a1:b2:c3"),
        ("00:01:02:a1:b2:c3:d4:e5", "00:01:02:a1:b2:c3:d4:e5"),
        (b"\x00\x01\x02\xA1\xB2\xC3", "00:01:02:a1:b2:c3"),
        (b"\x00\x01\x02\xa1\xb2\xc3\xd4\xe5", "00:01:02:a1:b2:c3:d4:e5"),
    ],
)
def test_eui_init(arg, address):
    assert str(EUI(arg)) == address


@pytest.mark.parametrize(
    "arg",
    [
        "foo",
        1234,
        "01:02:d3",
        b"\x01\x02\xd3",
    ],
)
def test_eui_invalid(arg):
    with pytest.raises(ValueError):
        EUI(arg)


def test_eui_bits():
    assert EUI("00:01:02:A1:B2:C3").bits == 48
    assert EUI("00:01:02:A1:B2:C3:D4:E5").bits == 64


def test_eui_eq():
    assert EUI("00:01:02:A1:B2:C3") == EUI("00:01:02:a1:b2:c3")
    assert EUI("00:01:02:A1:B2:C3") != EUI("00:01:02:a1:b2:c4")
    assert EUI("00:01:02:A1:B2:C3:D4:E5") == EUI("00:01:02:a1:b2:c3:d4:e5")
    assert EUI("00:01:02:A1:B2:C3:D4:E5") != EUI("00:01:02:a1:b2:c3")
