"""
Pytest config
"""

import asyncio
import difflib
import functools
import inspect
import logging
import os
import pty
import pytest
import traceback

from tests.buffers import HexBuffer
from tests.conftest_providers import *


collect_ignore = ["test_pb2.py"]


logger = logging.getLogger("conftest")


def pytest_configure(config):
    if config.option.logdebug:
        config.option.log_cli_level = "DEBUG"


def pytest_addoption(parser):
    parser.addoption("--logdebug", action="store_true", help="Enable debug logging")


def wrap_async_test(pyfuncitem, test_fn):
    service = pyfuncitem.funcargs.get("service", None)
    mqttbroker = pyfuncitem.funcargs.get("mqttbroker", None)

    @functools.wraps(test_fn)
    def wrapped_async_test(*args, **kwargs):
        async def async_test(*args, **kwargs):
            try:
                async with asyncio.timeout(1):
                    if mqttbroker:
                        await mqttbroker.start()

                    if service:
                        await service.start_background()

                        for name, value in kwargs.items():
                            if inspect.iscoroutine(value):
                                kwargs[name] = await value

                        await service.wait_start()

            except asyncio.TimeoutError:
                pytest.fail("Timed out during service setup")

            try:
                async with asyncio.timeout(5):
                    await test_fn(*args, **kwargs)
            except asyncio.TimeoutError as e:
                if e.__cause__:
                    frame = traceback.extract_tb(e.__cause__.__traceback__)[1]
                    errormsg = f"Timed out during test execution at {frame.filename}:{frame.lineno}"
                else:
                    errormsg = f"Timed out during test execution"

                logger.error(errormsg)
                pytest.fail(errormsg)
            finally:
                logger.info("Test completed")

            try:
                async with asyncio.timeout(1):
                    if service:
                        await service.stop_background()

                    if mqttbroker:
                        await mqttbroker.stop()
            except asyncio.TimeoutError:
                pytest.fail("Timed out during service shutdown")

        asyncio.run(async_test(*args, **kwargs))

    return wrapped_async_test


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    is_async = False
    if hasattr(pyfuncitem, "hypothesis"):
        if inspect.iscoroutinefunction(pyfuncitem.obj.hypothesis.inner_test):
            is_async = True
            pyfuncitem.obj.hypothesis.inner_test = wrap_async_test(
                pyfuncitem, pyfuncitem.obj.hypothesis.inner_test
            )
    elif inspect.iscoroutinefunction(pyfuncitem.obj):
        is_async = True
        pyfuncitem.obj = wrap_async_test(pyfuncitem, pyfuncitem.obj)

    if not is_async:
        assert (
            pyfuncitem.funcargs.get("service", None) is None
        ), "Test with service fixture must be a coroutine"


class Stdin:
    def __init__(self):
        self.master_fd, self.slave_fd = pty.openpty()
        self.reader = os.fdopen(self.master_fd)
        self.writer = open(os.ttyname(self.slave_fd), "w")

    def close(self):
        self.reader.close()
        self.writer.close()


@pytest.fixture
def stdin():
    stdin = Stdin()
    yield stdin
    stdin.close()


class Stdout:
    def __init__(self):
        self.value = ""
        self.dirty = False

    def write(self, data):
        self.value += data
        self.dirty = True

    def clear(self):
        self.value = ""
        self.dirty = False

    def flush(self):
        self.dirty = False


@pytest.fixture
def stdout():
    return Stdout()


class AnyInteger:
    def __eq__(self, other):
        if isinstance(other, int):
            return True
        return False


@pytest.fixture
def any_integer():
    return AnyInteger()


def pytest_assertrepr_compare(op, left, right):
    """
    Override the assertions of bytes, bytearrays, and HexBuffers to show the diff in
    hex format.
    """
    if op == "==":
        if isinstance(right, HexBuffer) and isinstance(left, (bytes, bytearray)):
            hex_left, hex_right = HexBuffer(left), right
        elif isinstance(right, (bytes, bytearray)) and isinstance(left, HexBuffer):
            hex_left, hex_right = left, HexBuffer(right)
        else:
            return None

        left_lines = repr(hex_left).splitlines()
        right_lines = repr(hex_right).splitlines()
        min_len = min(len(hex_left), len(hex_right))

        diff_index = next((i for i in range(min_len) if hex_left[i] != hex_right[i]), None)

        extra_item = hex_left[min_len] if len(hex_left) > len(hex_right) else hex_right[min_len] if min_len < max(len(hex_left), len(hex_right)) else None
        extra_msg = f", first extra item: {extra_item}" if extra_item is not None else ""

        return [
            f"{left_lines[0]} == {right_lines[0]}",
            *(f"                         {line}" for line in right_lines[1:]),
            f"At index {diff_index} diff: {hex_left[diff_index]} (0x{hex_left[diff_index]:02x}) != {hex_right[diff_index]} (0x{hex_right[diff_index]:02x})" if diff_index is not None else "",
            f"{'Left' if len(hex_left) > len(hex_right) else 'Right'} contains {abs(len(hex_left) - len(hex_right))} more items{extra_msg}",
            "Full diff:",
            *(f"- {line}" for line in left_lines),
            *(f"+ {line}" for line in right_lines)
        ]
