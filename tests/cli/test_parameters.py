"""
tests/cli/test_parameters.py
"""

import pytest

from routesia.cli import parameters


def test_bool_values():
    param = parameters.Bool()
    for value in ("1", "true", "t", "yes"):
        assert param(value) is True
    for value in ("0", "false", "f", "no"):
        assert param(value) is False


def test_list_values():
    param = parameters.List(parameters.Bool())
    assert param("t,f,1,0") == [True, False, True, False]

    param = parameters.List(parameters.String())
    assert param("foo,bar,1,0") == ["foo", "bar", "1", "0"]

    param = parameters.List(parameters.Int8())
    assert param("1,20,-100,127") == [1, 20, -100, 127]
    with pytest.raises(ValueError) as e:
        assert param("1,20,-100,128")
    assert str(e.value) == "Must be <= 127"


def test_compoundparameter_values():
    param = parameters.Compound(
        (
            ("ipaddress", parameters.IPAddress()),
            ("port", parameters.UInt16()),
        )
    )
    assert param("1.2.3.4:8000") == {
        "ipaddress": "1.2.3.4",
        "port": 8000,
    }

    with pytest.raises(ValueError) as e:
        assert param("1.2.3.4.5:8000")
    assert str(e.value) == "'1.2.3.4.5' does not appear to be an IPv4 or IPv6 address"

    with pytest.raises(ValueError) as e:
        assert param("1.2.3.4:8000000")
    assert str(e.value) == "Must be <= 65535"


def test_listparameter_compoundparameter_values():
    param = parameters.List(
        parameters.Compound(
            (
                ("ipaddress", parameters.IPAddress()),
                ("port", parameters.UInt16()),
            ),
            separator=";"
        )
    )
    assert param("1.2.3.4;8000,2001:db8::1;5789") == [
        {
            "ipaddress": "1.2.3.4",
            "port": 8000,
        },
        {
            "ipaddress": "2001:db8::1",
            "port": 5789,
        },
    ]
