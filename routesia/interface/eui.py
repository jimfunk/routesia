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
            if isinstance(address, str):
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
            raise ValueError(f"'{address}' does not appear to be an EUI-48 or EUI-64 address")

    def __str__(self) -> str:
        s = binascii.hexlify(self.data).decode()
        return ":".join(s[i:i+2] for i in range(0, len(self.data)*2, 2))

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other):
        return self.data == other.data

    @property
    def bits(self) -> int:
        if len(self.data) == 6:
            return 48
        return 64
