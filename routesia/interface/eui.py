"""
EUI hardware address objects
"""

import binascii


class EUI:
    """
    Represents an EUI-48 or EUI-64 hardware address.
    """

    def __init__(self, address: str | bytes):
        self.data: bytes

        try:
            if isinstance(address, EUI):
                data = address.data
            elif isinstance(address, str):
                data = binascii.unhexlify(address.replace(":", "").replace("-", ""))
            elif isinstance(address, bytes):
                data = address
            else:
                raise ValueError

            if len(data) in (6, 8):
                self.data = data
            else:
                raise ValueError
        except ValueError:
            raise ValueError(
                f"'{address}' does not appear to be an EUI-48 or EUI-64 address"
            )

    def __bytes__(self):
        return self.data

    def __str__(self) -> str:
        s = binascii.hexlify(self.data).decode()
        return ":".join(s[i : i + 2] for i in range(0, len(self.data) * 2, 2))

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other):
        if isinstance(other, EUI):
            return self.data == other.data
        if isinstance(other, (bytes, bytearray)):
            return self.data == bytes(other)
        return False

    def __hash__(self):
        return hash(self.data)

    @property
    def bits(self) -> int:
        if len(self.data) == 6:
            return 48
        return 64


class EUI48:
    """EUI-48 (6-byte) hardware address"""

    bits = 48

    def __init__(self, address: str | bytes):
        self.data: bytes

        try:
            if isinstance(address, EUI48):
                data = address.data
            elif isinstance(address, EUI):
                data = address.data
                if len(data) != 6:
                    raise ValueError("EUI48 requires exactly 6 bytes")
            elif isinstance(address, str):
                data = binascii.unhexlify(address.replace(":", "").replace("-", ""))
                if len(data) != 6:
                    raise ValueError("EUI48 requires exactly 6 bytes")
            elif isinstance(address, bytes):
                data = address
                if len(data) != 6:
                    raise ValueError("EUI48 requires exactly 6 bytes")
            else:
                raise ValueError

            self.data = data
        except ValueError:
            raise ValueError(f"'{address}' does not appear to be an EUI-48 address")

    def __bytes__(self):
        return self.data

    def __str__(self) -> str:
        s = binascii.hexlify(self.data).decode()
        return ":".join(s[i : i + 2] for i in range(0, len(self.data) * 2, 2))

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other):
        if isinstance(other, EUI48):
            return self.data == other.data
        if isinstance(other, EUI) and len(other.data) == 6:
            return self.data == other.data
        if isinstance(other, (bytes, bytearray)):
            return self.data == bytes(other)
        return False

    def __hash__(self):
        return hash(self.data)


class EUI64:
    """EUI-64 (8-byte) hardware address"""

    bits = 64

    def __init__(self, address: str | bytes):
        self.data: bytes

        try:
            if isinstance(address, EUI64):
                data = address.data
            elif isinstance(address, EUI):
                data = address.data
                if len(data) != 8:
                    raise ValueError("EUI64 requires exactly 8 bytes")
            elif isinstance(address, str):
                data = binascii.unhexlify(address.replace(":", "").replace("-", ""))
                if len(data) != 8:
                    raise ValueError("EUI64 requires exactly 8 bytes")
            elif isinstance(address, bytes):
                data = address
                if len(data) != 8:
                    raise ValueError("EUI64 requires exactly 8 bytes")
            else:
                raise ValueError

            self.data = data
        except ValueError:
            raise ValueError(f"'{address}' does not appear to be an EUI-64 address")

    def __bytes__(self):
        return self.data

    def __str__(self) -> str:
        s = binascii.hexlify(self.data).decode()
        return ":".join(s[i : i + 2] for i in range(0, len(self.data) * 2, 2))

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other):
        if isinstance(other, EUI64):
            return self.data == other.data
        if isinstance(other, EUI) and len(other.data) == 8:
            return self.data == other.data
        if isinstance(other, (bytes, bytearray)):
            return self.data == bytes(other)
        return False

    def __hash__(self):
        return hash(self.data)
