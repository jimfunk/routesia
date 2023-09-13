import pytest

from routesia.cli.keyreader import KeyReader, Key


async def test_read_character(stdin):
    with KeyReader(infile=stdin.reader) as reader:
        stdin.writer.write("a")
        stdin.writer.flush()
        key = await reader.get()
        assert key == "a"


async def test_read_multiple_characters(stdin):
    with KeyReader(infile=stdin.reader) as reader:
        stdin.writer.write("abcd")
        stdin.writer.flush()
        assert await reader.get() == "a"
        assert await reader.get() == "b"
        assert await reader.get() == "c"
        assert await reader.get() == "d"


@pytest.mark.parametrize(
    "char,key",
    [
        ("\x00", Key.NULL),
        ("\x01", Key.HOME),
        ("\x02", Key.LEFT),
        ("\x03", Key.INTERRUPT),
        ("\x04", Key.EOF),
        ("\x05", Key.END),
        ("\x06", Key.RIGHT),
        ("\x07", Key.BEL),
        ("\x08", Key.DELETE_LEFT),
        ("\x09", Key.TAB),
        ("\x0a", Key.ENTER),
        ("\x0b", Key.CUT_ALL_RIGHT),
        ("\x0c", Key.CLEAR),
        ("\x0d", Key.ENTER),
        ("\x0e", Key.DOWN),
        ("\x0f", Key.ENTER),
        ("\x10", Key.UP),
        ("\x11", Key.RESUME),
        ("\x12", Key.REVERSE_SEARCH),
        ("\x13", Key.SUSPEND),
        ("\x14", Key.SWITCH_CHARS),
        ("\x15", Key.CUT_ALL_LEFT),
        ("\x16", Key.UNESCAPE),
        ("\x17", Key.CUT_WORD_LEFT),
        ("\x18", Key.CANCEL),
        ("\x19", Key.PASTE),
        ("\x1a", Key.BACKGROUND),
        ("\x1c", Key.NULL),
        ("\x1d", Key.NULL),
        ("\x1e", Key.NULL),
        ("\x1f", Key.NULL),
        ("\x7f", Key.DELETE_LEFT),
    ]
)
async def test_read_control_key(stdin, char, key):
    with KeyReader(infile=stdin.reader) as reader:
        stdin.writer.write(char)
        stdin.writer.flush()
        assert await reader.get() == key


@pytest.mark.parametrize(
    "sequence,key",
    [
        ("\x1b[3~", Key.DELETE_RIGHT),
        ("\x1b[A", Key.UP),
        ("\x1b[B", Key.DOWN),
        ("\x1b[C", Key.RIGHT),
        ("\x1b[D", Key.LEFT),
        ("\x1bb", Key.WORD_LEFT),
        ("\x1bB", Key.WORD_LEFT),
        ("\x1bf", Key.WORD_RIGHT),
        ("\x1bF", Key.WORD_RIGHT),
    ]
)
async def test_read_escape_sequence(stdin, sequence, key):
    with KeyReader(infile=stdin.reader) as reader:
        stdin.writer.write(sequence)
        stdin.writer.flush()
        assert await reader.get() == key


async def test_read_escape_unmatched(stdin):
    with KeyReader(infile=stdin.reader) as reader:
        stdin.writer.write("\x1b0")
        stdin.writer.flush()
        assert await reader.get() == Key.ESCAPE
        assert await reader.get() == "0"
