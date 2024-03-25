"""
routesia/cli/types.py - Types used for argument parsing and validation
"""
import re


class Int8(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not -128 <= value <= 127:
            raise ValueError("must be between -128 and 127 inclusive")
        return super(cls, cls).__new__(cls, value)


class Int16(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not -32768 <= value <= 32767:
            raise ValueError("must be between -32768 and 32767 inclusive")
        return super(cls, cls).__new__(cls, value)


class Int32(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not -2147483648 <= value <= 2147483647:
            raise ValueError("must be between -2147483648 and 2147483647 inclusive")
        return super(cls, cls).__new__(cls, value)


class Int64(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not -9223372036854775808 <= value <= 9223372036854775807:
            raise ValueError("must be between -9223372036854775808 and 9223372036854775807 inclusive")
        return super(cls, cls).__new__(cls, value)


class UInt8(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not 0 <= value <= 255:
            raise ValueError("must be between 0 and 255 inclusive")
        return super(cls, cls).__new__(cls, value)


class UInt16(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not 0 <= value <= 65535:
            raise ValueError("must be between 0 and 65535 inclusive")
        return super(cls, cls).__new__(cls, value)


class UInt32(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not 0 <= value <= 4294967295:
            raise ValueError("must be between 0 and 4294967295 inclusive")
        return super(cls, cls).__new__(cls, value)


class UInt64(int):
    def __new__(cls, value, *args, **kwargs):
        value = int(value)
        if not 0 <= value <= 18446744073709551615:
            raise ValueError("must be between 0 and 18446744073709551615 inclusive")
        return super(cls, cls).__new__(cls, value)


class EUI:
    EUI_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

    def __init__(self, value: str):
        if not self.EUI_RE.fullmatch(value):
            raise ValueError("invalid EUI hardware address")
        self.value = value

    def __str__(self):
        return self.value
