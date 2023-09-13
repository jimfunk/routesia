from collections import deque
import ctypes
import os
from typing import Any

libc = ctypes.cdll.LoadLibrary("libc.so.6")

eventfd = libc.eventfd

# From bits/eventfd.h
#
EFD_SEMAPHORE = 0o0000001
EFD_NONBLOCK = 0o0004000


class EventQueue:
    """
    A strictly non-blocking queue class based on eventfd.

    The use of eventfd allows for simple thread-safety and integration in
    various event loops.
    """
    def __init__(self) -> None:
        self.dq = deque()
        self.fd = eventfd(0, EFD_SEMAPHORE | EFD_NONBLOCK)

    def fileno(self) -> int:
        return self.fd

    def close(self) -> None:
        os.close(self.fd)

    def put(self, item: Any) -> None:
        self.dq.append(item)
        os.write(self.fd, bytearray(ctypes.c_uint64(1)))

    def get(self) -> Any:
        os.read(self.fd, ctypes.sizeof(ctypes.c_uint64))
        return self.dq.popleft()
