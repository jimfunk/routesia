"""
hosteria/cli/keyreader.py - Keypress reader for CLI
"""

from curses import ascii
import asyncio
from enum import Enum
import os
import sys
import termios
import tty
from typing import Union


class Key(Enum):
    """
    Represents a non-character keypress
    """
    NULL = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
    WORD_LEFT = 5
    WORD_RIGHT = 6
    HOME = 7
    END = 8
    ENTER = 9
    DELETE_LEFT = 10
    DELETE_RIGHT = 11
    SWITCH_CHARS = 12
    TAB = 13
    SHIFT_TAB = 14
    CUT_ALL_LEFT = 15
    CUT_ALL_RIGHT = 16
    CUT_WORD_LEFT = 17
    PASTE = 18
    INTERRUPT = 19
    EOF = 20
    ESCAPE = 21
    REVERSE_SEARCH = 22
    CLEAR = 23
    UNESCAPE = 24
    BEL = 25
    SUSPEND = 26
    RESUME = 27
    CANCEL = 28
    BACKGROUND = 29


class EscapeSequenceNode:
    def __init__(self):
        self.key = None
        self.children = {}

    def set_key(self, key: Key):
        self.key = key

    def match(self, sequence):
        if not sequence:
            return self
        if sequence[0] in self.children:
            return self.children[sequence[0]].match(sequence[1:])
        return None


class EscapeSequenceTree:
    """
    Tree used for matching escape sequences.
    """
    def __init__(self):
        self.root = EscapeSequenceNode()

    def add(self, sequence: str, key: Key):
        node = self.root
        for char in sequence:
            if char in node.children:
                node = node.children[char]
            else:
                new_node = EscapeSequenceNode()
                node.children[char] = new_node
                node = new_node

        node.set_key(key)

    def match(self, sequence: str) -> Union[EscapeSequenceNode, None]:
        """
        Match an escape sequence

        If a node is matched, it will be returned. For a complete match, the
        node's ``key`` property will be set. For a partial match it will be
        unset.

        If None is returned, there is no possible match for the sequence, even
        if more characters are added.
        """
        return self.root.match(sequence)


ESCAPE_SEQUENCE_TREE = EscapeSequenceTree()
ESCAPE_SEQUENCE_TREE.add("\x1b[3~", Key.DELETE_RIGHT)
ESCAPE_SEQUENCE_TREE.add("\x1b[A", Key.UP)
ESCAPE_SEQUENCE_TREE.add("\x1b[B", Key.DOWN)
ESCAPE_SEQUENCE_TREE.add("\x1b[C", Key.RIGHT)
ESCAPE_SEQUENCE_TREE.add("\x1b[D", Key.LEFT)
ESCAPE_SEQUENCE_TREE.add("\x1b[Z", Key.SHIFT_TAB)
ESCAPE_SEQUENCE_TREE.add("\x1bb", Key.WORD_LEFT)
ESCAPE_SEQUENCE_TREE.add("\x1bB", Key.WORD_LEFT)
ESCAPE_SEQUENCE_TREE.add("\x1bf", Key.WORD_RIGHT)
ESCAPE_SEQUENCE_TREE.add("\x1bF", Key.WORD_RIGHT)


ASCII_CONTROL_KEY_MAP = {
    "\x00": Key.NULL,
    "\x01": Key.HOME,  # Ctrl-A
    "\x02": Key.LEFT,  # Ctrl-B
    "\x03": Key.INTERRUPT,  # Ctrl-C
    "\x04": Key.EOF,  # Ctrl-D
    "\x05": Key.END,  # Ctrl-E
    "\x06": Key.RIGHT,  # Ctrl-F
    "\x07": Key.BEL,  # Ctrl-G
    "\x08": Key.DELETE_LEFT,  # Ctrl-H
    "\x09": Key.TAB,  # Ctrl-I
    "\x0a": Key.ENTER,  # Ctrl-J
    "\x0b": Key.CUT_ALL_RIGHT,  # Ctrl-K
    "\x0c": Key.CLEAR,  # Ctrl-L
    "\x0d": Key.ENTER,  # Ctrl-M
    "\x0e": Key.DOWN,  # Ctrl-N
    "\x0f": Key.ENTER,  # Ctrl-O
    "\x10": Key.UP,  # Ctrl-P
    "\x11": Key.RESUME,  # Ctrl-Q
    "\x12": Key.REVERSE_SEARCH,  # Ctrl-R
    "\x13": Key.SUSPEND,  # Ctrl-S
    "\x14": Key.SWITCH_CHARS,  # Ctrl-T
    "\x15": Key.CUT_ALL_LEFT,  # Ctrl-U
    "\x16": Key.UNESCAPE,  # Ctrl-V
    "\x17": Key.CUT_WORD_LEFT,  # Ctrl-W
    "\x18": Key.CANCEL,  # Ctrl-X
    "\x19": Key.PASTE,  # Ctrl-Y
    "\x1a": Key.BACKGROUND,  # Ctrl-Z
    "\x1b": Key.ESCAPE,
    "\x1c": Key.NULL,
    "\x1d": Key.NULL,
    "\x1e": Key.NULL,
    "\x1f": Key.NULL,
    "\x7f": Key.DELETE_LEFT,
}


class KeyReader:
    """
    Reads keypresses from an input file, normally ``sys.stdin``.

    It is expected to be used as a context manager, eg::

        with KeyReader() as reader:
            while True:
                key = await reader.get()
                ...

    Each key will either be a normal character, or a ``Key`` instance
    representing a keypress.
    """
    def __init__(self, infile=sys.stdin, max_len=65535):
        self.infile = infile
        self.key_queue = asyncio.Queue(maxsize=max_len)
        self.term_attrs = None
        self.blocking = None
        self.loop = None
        self.escape_sequence = None
        self.unescape = False

    def __enter__(self):
        self.term_attrs = termios.tcgetattr(self.infile)
        self.loop = asyncio.get_running_loop()
        self.loop.add_reader(self.infile.fileno(), self.handle_read)
        tty.setraw(self.infile)
        self.blocking = os.get_blocking(self.infile.fileno())
        os.set_blocking(self.infile.fileno(), False)
        return self

    def __exit__(self, type, value, traceback):
        os.set_blocking(self.infile.fileno(), self.blocking)
        self.loop.remove_reader(self.infile.fileno())
        termios.tcsetattr(self.infile, termios.TCSAFLUSH, self.term_attrs)

    def handle_read(self):
        keys = list(self.infile.read(65535))
        while keys:
            key = keys.pop(0)
            if self.escape_sequence:
                self.escape_sequence += key
                self.check_escape()
                continue
            if self.unescape:
                # Don't escape the next key
                self.key_queue.put_nowait(key)
                self.unescape = False
                continue
            if ascii.iscntrl(key):
                if key == "\x22":  # Ctrl-V
                    self.unescape = True
                if key == "\x1b":  # ESC
                    # Start of escape sequence
                    self.escape_sequence = key
                else:
                    self.key_queue.put_nowait(ASCII_CONTROL_KEY_MAP[key])
                continue
            self.key_queue.put_nowait(key)

    def check_escape(self):
        result = ESCAPE_SEQUENCE_TREE.match(self.escape_sequence)
        if result is None:
            # No match, release as individual keys
            self.key_queue.put_nowait(Key.ESCAPE)
            for char in self.escape_sequence[1:]:
                if ascii.iscntrl(char):
                    self.key_queue.put_nowait(ASCII_CONTROL_KEY_MAP[char])
                else:
                    self.key_queue.put_nowait(char)
            self.escape_sequence = None
            return
        if result.key:
            self.key_queue.put_nowait(result.key)
            self.escape_sequence = None
        # Otherwise, we have a partial match. Wait for more characters

    async def get(self) -> Union[str, Key]:
        """
        Returns a single key
        """
        return await self.key_queue.get()
