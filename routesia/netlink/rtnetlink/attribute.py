from ctypes import (
    Structure,
    c_uint16,
    sizeof,
)


def rta_align(length: int) -> int:
    """
    Get the space required for length after alignment
    """
    return (length + 3) & ~3


def rta_length(payload_len: int) -> int:
    """
    Get the length of payload plus header
    """
    return payload_len + sizeof(RTAttribute)


def rta_space(payload_len: int) -> int:
    """
    Get the full space required for payload plus header after alignment
    """
    return rta_align(rta_length(payload_len))


class RTAttribute(Structure):
    """
    Rtnetlink attribute header
    """

    _fields_ = [
        ("rta_len", c_uint16),
        ("rta_type", c_uint16),
    ]
    rta_len: int
    rta_type: int

    def __init__(self, rta_type: int, payload: bytes) -> None:
        super().__init__(rta_type=rta_type, rta_len=rta_length(len(payload)))
        self.payload = payload

    def __len__(self) -> int:
        return rta_align(self.rta_len)

    def __bytes__(self):
        padding = b"\x00" * (len(self) - self.rta_len)
        return bytes(memoryview(self)) + self.payload + padding

    @classmethod
    def from_buffer(
        cls, buffer: bytes | bytearray | memoryview, offset: int = 0
    ) -> "RTAttribute":
        obj = type(Structure).from_buffer(cls, buffer, offset)
        if len(buffer) < offset + obj.rta_len:
            raise ValueError("Buffer is too small for the given rta_len")
        payload_len = obj.rta_len - sizeof(cls)
        payload_idx = offset + sizeof(cls)
        obj.payload = buffer[payload_idx : payload_idx + payload_len]
        return obj

    @classmethod
    def from_buffer_copy(
        cls, buffer: bytes | bytearray | memoryview, offset: int = 0
    ) -> "RTAttribute":
        obj = type(Structure).from_buffer_copy(cls, buffer, offset)
        if len(buffer) < offset + obj.rta_len:
            raise ValueError("Buffer is too small for the given rta_len")
        payload_len = obj.rta_len - sizeof(cls)
        payload_idx = offset + sizeof(cls)
        obj.payload = buffer[payload_idx : payload_idx + payload_len]
        return obj
