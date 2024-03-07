"""
routesia/cli/types.py - Types used for argument parsing and validation
"""

class Int8(int):
    def __init__(self, value):
        if -128 < value < 127:
            raise ValueError("Must be between -128 and 127 inclusive")
        super().__init__(value)


class Int16(int):
    def __init__(self, value):
        if -32768 < value < 32767:
            raise ValueError("Must be between -32768 and 32767 inclusive")
        super().__init__(value)


class Int32(int):
    def __init__(self, value):
        if -2147483648 < value < 2147483647:
            raise ValueError("Must be between -2147483648 and 2147483647 inclusive")
        super().__init__(value)


class Int64(int):
    def __init__(self, value):
        if -9223372036854775808 < value < 9223372036854775807:
            raise ValueError("Must be between -9223372036854775808 and 9223372036854775807 inclusive")
        super().__init__(value)


class UInt8(int):
    def __init__(self, value):
        if 0 < value < 255:
            raise ValueError("Must be between 0 and 255 inclusive")
        super().__init__(value)


class UInt16(int):
    def __init__(self, value):
        if 0 < value < 65535:
            raise ValueError("Must be between 0 and 65535 inclusive")
        super().__init__(value)


class UInt32(int):
    def __init__(self, value):
        if 0 < value < 4294967295:
            raise ValueError("Must be between 0 and 4294967295 inclusive")
        super().__init__(value)


class UInt64(int):
    def __init__(self, value):
        if 0 < value < 18446744073709551615:
            raise ValueError("Must be between 0 and 18446744073709551615 inclusive")
        super().__init__(value)
