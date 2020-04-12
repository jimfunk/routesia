"""
routesia/cli/parameters.py - Parameter definition and processing for command line arguments
"""

import ipaddress
import re


class Parameter:
    def __init__(self, required=False, completer=None):
        self.required = required
        self.completer = completer

    def __call__(self, value):
        raise NotImplementedError

    async def get_completions(self, client, suggestion, **kwargs):
        if self.completer:
            return await self.completer(client, suggestion, **kwargs)
        return []


class Bool(Parameter):
    def __call__(self, value):
        value = value.lower()
        if value in ('1', 'true', 't', 'yes'):
            return True
        return False

    async def get_completions(self, client, suggestion, **kwargs):
        return ('true', 'false')


class String(Parameter):
    def __init__(self, min_length=None, max_length=None, regex=None, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length
        self.min_length = min_length
        self.regex = re.compile(regex) if regex else None

    def __call__(self, value):
        if value is None:
            value = ""
        else:
            value = str(value)
        if self.regex:
            if not self.regex.match(value):
                raise ValueError("Must match regex %s" % self.regex.pattern)
        return value


class IPAddress(Parameter):
    def __call__(self, value):
        if value != '':
            value = str(ipaddress.ip_address(value))
        return value


class IPInterface(Parameter):
    def __call__(self, value):
        if value != '':
            value = (ipaddress.ip_interface(value))
        return value


class IPNetwork(Parameter):
    def __call__(self, value):
        if value != '':
            value = str(ipaddress.ip_network(value))
        return value


class HardwareAddress(String):
    def __init__(self, **kwargs):
        super().__init__(regex=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', **kwargs)


class Int16(Parameter):
    def __init__(self, min=-32768, max=32767, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i > self.max:
            raise ValueError("Must be > %s" % self.max)
        return i


class Int32(Parameter):
    def __init__(self, min=-2147483648, max=2147483647, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i > self.max:
            raise ValueError("Must be > %s" % self.max)
        return i


class Int64:
    def __init__(
        self, min=-9223372036854775808, max=9223372036854775807, **kwargs
    ):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i > self.max:
            raise ValueError("Must be > %s" % self.max)
        return i


class UInt16(Parameter):
    def __init__(self, min=0, max=65535, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i > self.max:
            raise ValueError("Must be > %s" % self.max)
        return i


class UInt32(Parameter):
    def __init__(self, min=0, max=4294967295, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i > self.max:
            raise ValueError("Must be > %s" % self.max)
        return i


class UInt64:
    def __init__(self, min=0, max=18446744073709551615, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i > self.max:
            raise ValueError("Must be > %s" % self.max)
        return i


class ProtobufEnum(Parameter):
    """
    Wraps a protobuf enum for use as a type converting a string to the
    emnumerated value.
    """

    def __init__(self, enum, **kwargs):
        super().__init__(**kwargs)
        self.enum = enum

    def __call__(self, value):
        if value is None:
            return self.enum.values()[0]
        return self.enum.Value(value)

    async def get_completions(self, client, suggestion, **kwargs):
        if self.completer:
            return await self.completer(client, suggestion, **kwargs)
        return [key for key in self.enum.keys() if key.startswith(suggestion)]
