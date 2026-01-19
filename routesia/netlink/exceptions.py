class NetlinkError(Exception):
    def __init__(self, error_code, message):
        self.error_code = error_code
        self.message = message
        super().__init__(f"Netlink error {error_code}: {message}")


class NetlinkMessageException(Exception):
    pass
