class HexBuffer(bytearray):
    def __init__(self, hexdata: str | bytes):
        if isinstance(hexdata, bytes) or isinstance(hexdata, bytearray):
            return super().__init__(hexdata)
        else:
            return super().__init__(bytes.fromhex("".join(hexdata.split())))

    def __repr__(self):
        lines = []
        current_line = []

        for i, b in enumerate(self):
            if i % 16 == 0 and i != 0:
                lines.append(" ".join(current_line))
                current_line = []
            elif i % 8 == 0 and i != 0:
                current_line.append(" ")

            current_line.append(f"{b:02x}")

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def __eq__(self, other):
        if isinstance(other, (bytes, bytearray)):
            other = HexBuffer(other)
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)
