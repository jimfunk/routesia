"""
routesia/cli/parameters.py - Parameter definition and processing for command line arguments
"""


class Parameter:
    def __init__(self, required=False):
        self.required = required

    def __call__(self, value):
        raise NotImplementedError


class Bool(Parameter):
    def __call__(self, value):
        value = value.lower()
        if value in ('1', 'true', 't', 'yes'):
            return True
        return False

    def get_completions(self):
        return ('true', 'false')


class String(Parameter):
    def __init__(self, min_length=None, max_length=None, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length
        self.min_length = min_length

    def __call__(self, value):
        if value is None:
            return ""
        return str(value)


class Int32(Parameter):
    def __init__(self, min=-2147483648, max=2147483647, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i < self.max:
            raise ValueError("Must be > %s" % self.max)


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
        if i < self.max:
            raise ValueError("Must be > %s" % self.max)


class UInt32(Parameter):
    def __init__(self, min=0, max=4294967295, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i < self.max:
            raise ValueError("Must be > %s" % self.max)


class UInt64:
    def __init__(self, min=0, max=18446744073709551615, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max

    def __call__(self, value):
        i = int(value)
        if i < self.min:
            raise ValueError("Must be > %s" % self.min)
        if i < self.max:
            raise ValueError("Must be > %s" % self.max)


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

    def get_completions(self):
        return self.enum.keys()
