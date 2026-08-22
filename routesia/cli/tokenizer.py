"""
routesia/cli/tokenizer.py - CLI input tokenization

The interactive prompt lets an argument contain a space when it is enclosed
in double quotes (for example, a rule description). Splitting on plain
whitespace would clip that argument into several tokens.
"""
from dataclasses import dataclass


@dataclass
class Token:
    """
    Represents a token within a command input
    """
    value: str
    start: int
    end: int


def tokenize(text: str) -> "list[Token]":
    """
    Split ``text`` into a list of :class:`Token`.

    ``value`` is the token content without surrounding quotes, and
    ``start`` and ``end`` are the character offsets in ``text`` spanned by
    the token. The offsets are needed by the prompt to edit and complete
    inside the raw input buffer.

    A double-quoted substring is a single token even when it contains
    whitespace. Inside a quoted value, a backslash escapes the next
    character only when that character is a quote or another backslash:
    ``\\"`` produces a literal quote and ``\\\\`` produces a literal
    backslash. Any other backslash is kept as-is. An opening quote with no
    closing quote consumes the rest of the string, so a command that is
    still being typed can still be tokenized.
    """
    tokens = []
    index = 0
    length = len(text)
    while index < length:
        if text[index] in " \t":
            index += 1
            continue
        start = index
        if text[index] == '"':
            index += 1
            value = []
            while index < length and text[index] != '"':
                is_escape = (
                    text[index] == "\\"
                    and index + 1 < length
                    and text[index + 1] in ("\\", '"')
                )
                if is_escape:
                    value.append(text[index + 1])
                    index += 2
                else:
                    value.append(text[index])
                    index += 1
            if index < length:
                # text[index] is the closing quote
                index += 1
            tokens.append(Token("".join(value), start, index))
        else:
            end = index
            while end < length and text[end] not in " \t":
                end += 1
            tokens.append(Token(text[index:end], start, end))
            index = end
    return tokens
