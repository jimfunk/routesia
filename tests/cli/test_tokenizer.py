from routesia.cli.tokenizer import Token, tokenize


def test_tokenize_empty():
    assert tokenize("") == []


def test_tokenize_single():
    assert tokenize("foo") == [Token("foo", 0, 3)]


def test_tokenize_multiple():
    assert tokenize("foo bar baz") == [
        Token("foo", 0, 3),
        Token("bar", 4, 7),
        Token("baz", 8, 11),
    ]


def test_tokenize_leading_whitespace():
    assert tokenize("  foo") == [Token("foo", 2, 5)]


def test_tokenize_repeated_whitespace():
    assert tokenize("foo   bar") == [
        Token("foo", 0, 3),
        Token("bar", 6, 9),
    ]


def test_tokenize_whitespace_inside_quotes():
    assert tokenize('foo "bar baz"') == [
        Token("foo", 0, 3),
        Token("bar baz", 4, 13),
    ]


def test_tokenize_token_after_quotes():
    assert tokenize('foo "bar baz" quux') == [
        Token("foo", 0, 3),
        Token("bar baz", 4, 13),
        Token("quux", 14, 18),
    ]


def test_tokenize_unclosed_quote():
    assert tokenize('foo "bar baz') == [
        Token("foo", 0, 3),
        Token("bar baz", 4, 12),
    ]


def test_tokenize_quote_offset():
    assert tokenize('x = "hello world"') == [
        Token("x", 0, 1),
        Token("=", 2, 3),
        Token("hello world", 4, 17),
    ]


def test_token_values_with_quotes():
    assert [token.value for token in tokenize('foo "bar baz" quux')] == [
        "foo",
        "bar baz",
        "quux",
    ]


def test_token_values_unclosed_quote():
    assert [token.value for token in tokenize('foo "bar baz')] == [
        "foo",
        "bar baz",
    ]


def test_token_values_plain():
    assert [token.value for token in tokenize("foo bar baz")] == [
        "foo",
        "bar",
        "baz",
    ]


def test_tokenize_escaped_quote():
    assert tokenize(r'foo "bar \"baz\""') == [
        Token("foo", 0, 3),
        Token('bar "baz"', 4, 17),
    ]


def test_tokenize_escaped_backslash():
    assert tokenize(r'"a\\"') == [Token("a\\", 0, 5)]


def test_tokenize_escaped_backslash_before_quote():
    assert tokenize(r'"a\\" b"') == [
        Token("a\\", 0, 5),
        Token('b"', 6, 8),
    ]


def test_tokenize_lone_backslash_is_literal():
    assert tokenize(r'"a\b"') == [Token(r"a\b", 0, 5)]
