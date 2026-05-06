"""Clean-room JSON implementation for Theseus.

Implements dumps, loads, dump, load without using the standard json module.
Pure Python, standard library only.
"""

# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

_ESCAPE_MAP = {
    '"': '\\"',
    '\\': '\\\\',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}


def _encode_string(s):
    out = ['"']
    for ch in s:
        if ch in _ESCAPE_MAP:
            out.append(_ESCAPE_MAP[ch])
            continue
        cp = ord(ch)
        if cp < 0x20:
            out.append('\\u%04x' % cp)
        elif cp < 0x7F:
            out.append(ch)
        else:
            # Always escape non-ASCII to ensure ASCII-safe output.
            if cp > 0xFFFF:
                # Encode as UTF-16 surrogate pair.
                v = cp - 0x10000
                high = 0xD800 | (v >> 10)
                low = 0xDC00 | (v & 0x3FF)
                out.append('\\u%04x\\u%04x' % (high, low))
            else:
                out.append('\\u%04x' % cp)
    out.append('"')
    return ''.join(out)


def _encode(obj):
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, bool):
        # Defensive: bool is subclass of int; handled above.
        return "true" if obj else "false"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return "NaN"
        if obj == float('inf'):
            return "Infinity"
        if obj == float('-inf'):
            return "-Infinity"
        # repr gives a round-trippable representation in Python.
        return repr(obj)
    if isinstance(obj, str):
        return _encode_string(obj)
    if isinstance(obj, (list, tuple)):
        return "[" + ", ".join(_encode(item) for item in obj) + "]"
    if isinstance(obj, dict):
        parts = []
        for key, value in obj.items():
            if isinstance(key, str):
                key_str = key
            elif isinstance(key, bool):
                key_str = "true" if key else "false"
            elif key is None:
                key_str = "null"
            elif isinstance(key, (int, float)):
                key_str = _encode(key).strip('"')
            else:
                raise TypeError(
                    "keys must be str, int, float, bool or None, "
                    "not %s" % type(key).__name__
                )
            parts.append(_encode_string(key_str) + ": " + _encode(value))
        return "{" + ", ".join(parts) + "}"
    raise TypeError(
        "Object of type %s is not JSON serializable" % type(obj).__name__
    )


def dumps(obj):
    """Serialize obj to a JSON-formatted string."""
    return _encode(obj)


def dump(obj, fp):
    """Serialize obj as JSON and write to file-like object fp."""
    fp.write(_encode(obj))


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

_WHITESPACE = ' \t\n\r'
_DIGITS = '0123456789'


class _Parser:
    __slots__ = ('s', 'pos', 'n')

    def __init__(self, s):
        if not isinstance(s, str):
            raise TypeError("the JSON object must be str, not %s" % type(s).__name__)
        self.s = s
        self.pos = 0
        self.n = len(s)

    def _skip_ws(self):
        s = self.s
        n = self.n
        p = self.pos
        while p < n and s[p] in _WHITESPACE:
            p += 1
        self.pos = p

    def _peek(self):
        if self.pos >= self.n:
            raise ValueError("Unexpected end of input at position %d" % self.pos)
        return self.s[self.pos]

    def parse_value(self):
        self._skip_ws()
        if self.pos >= self.n:
            raise ValueError("Empty document")
        ch = self.s[self.pos]
        if ch == '"':
            return self._parse_string()
        if ch == '{':
            return self._parse_object()
        if ch == '[':
            return self._parse_array()
        if ch == 't' or ch == 'f':
            return self._parse_bool()
        if ch == 'n':
            return self._parse_null()
        if ch == '-' or ch in _DIGITS:
            return self._parse_number()
        raise ValueError(
            "Unexpected character %r at position %d" % (ch, self.pos)
        )

    def _parse_string(self):
        s = self.s
        n = self.n
        # Skip opening quote.
        self.pos += 1
        out = []
        while self.pos < n:
            ch = s[self.pos]
            if ch == '"':
                self.pos += 1
                return ''.join(out)
            if ch == '\\':
                self.pos += 1
                if self.pos >= n:
                    raise ValueError("Unterminated escape sequence")
                esc = s[self.pos]
                self.pos += 1
                if esc == '"':
                    out.append('"')
                elif esc == '\\':
                    out.append('\\')
                elif esc == '/':
                    out.append('/')
                elif esc == 'b':
                    out.append('\b')
                elif esc == 'f':
                    out.append('\f')
                elif esc == 'n':
                    out.append('\n')
                elif esc == 'r':
                    out.append('\r')
                elif esc == 't':
                    out.append('\t')
                elif esc == 'u':
                    if self.pos + 4 > n:
                        raise ValueError("Incomplete \\u escape at position %d" % self.pos)
                    hex_str = s[self.pos:self.pos + 4]
                    try:
                        cp = int(hex_str, 16)
                    except ValueError:
                        raise ValueError(
                            "Invalid \\u escape %r at position %d" % (hex_str, self.pos)
                        )
                    self.pos += 4
                    # Handle UTF-16 surrogate pair.
                    if 0xD800 <= cp <= 0xDBFF:
                        if (self.pos + 6 <= n
                                and s[self.pos] == '\\'
                                and s[self.pos + 1] == 'u'):
                            low_hex = s[self.pos + 2:self.pos + 6]
                            try:
                                low = int(low_hex, 16)
                            except ValueError:
                                low = -1
                            if 0xDC00 <= low <= 0xDFFF:
                                cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00)
                                self.pos += 6
                    out.append(chr(cp))
                else:
                    raise ValueError(
                        "Invalid escape character %r at position %d"
                        % (esc, self.pos - 1)
                    )
            else:
                cp = ord(ch)
                if cp < 0x20:
                    raise ValueError(
                        "Invalid control character at position %d" % self.pos
                    )
                out.append(ch)
                self.pos += 1
        raise ValueError("Unterminated string starting at position %d" % self.pos)

    def _parse_number(self):
        s = self.s
        n = self.n
        start = self.pos
        if s[self.pos] == '-':
            self.pos += 1
        if self.pos >= n or s[self.pos] not in _DIGITS:
            raise ValueError("Invalid number at position %d" % start)
        # Integer part.
        if s[self.pos] == '0':
            self.pos += 1
        else:
            while self.pos < n and s[self.pos] in _DIGITS:
                self.pos += 1
        is_float = False
        # Fractional part.
        if self.pos < n and s[self.pos] == '.':
            is_float = True
            self.pos += 1
            if self.pos >= n or s[self.pos] not in _DIGITS:
                raise ValueError("Invalid number at position %d" % start)
            while self.pos < n and s[self.pos] in _DIGITS:
                self.pos += 1
        # Exponent part.
        if self.pos < n and s[self.pos] in 'eE':
            is_float = True
            self.pos += 1
            if self.pos < n and s[self.pos] in '+-':
                self.pos += 1
            if self.pos >= n or s[self.pos] not in _DIGITS:
                raise ValueError("Invalid number at position %d" % start)
            while self.pos < n and s[self.pos] in _DIGITS:
                self.pos += 1
        text = s[start:self.pos]
        if is_float:
            return float(text)
        return int(text)

    def _parse_bool(self):
        s = self.s
        if s[self.pos:self.pos + 4] == 'true':
            self.pos += 4
            return True
        if s[self.pos:self.pos + 5] == 'false':
            self.pos += 5
            return False
        raise ValueError("Invalid literal at position %d" % self.pos)

    def _parse_null(self):
        if self.s[self.pos:self.pos + 4] == 'null':
            self.pos += 4
            return None
        raise ValueError("Invalid literal at position %d" % self.pos)

    def _parse_array(self):
        self.pos += 1  # consume '['
        result = []
        self._skip_ws()
        if self.pos < self.n and self.s[self.pos] == ']':
            self.pos += 1
            return result
        while True:
            result.append(self.parse_value())
            self._skip_ws()
            if self.pos >= self.n:
                raise ValueError("Unterminated array")
            ch = self.s[self.pos]
            if ch == ',':
                self.pos += 1
                self._skip_ws()
                continue
            if ch == ']':
                self.pos += 1
                return result
            raise ValueError(
                "Expected ',' or ']' at position %d" % self.pos
            )

    def _parse_object(self):
        self.pos += 1  # consume '{'
        result = {}
        self._skip_ws()
        if self.pos < self.n and self.s[self.pos] == '}':
            self.pos += 1
            return result
        while True:
            self._skip_ws()
            if self.pos >= self.n or self.s[self.pos] != '"':
                raise ValueError(
                    "Expected string key at position %d" % self.pos
                )
            key = self._parse_string()
            self._skip_ws()
            if self.pos >= self.n or self.s[self.pos] != ':':
                raise ValueError(
                    "Expected ':' at position %d" % self.pos
                )
            self.pos += 1
            value = self.parse_value()
            result[key] = value
            self._skip_ws()
            if self.pos >= self.n:
                raise ValueError("Unterminated object")
            ch = self.s[self.pos]
            if ch == ',':
                self.pos += 1
                continue
            if ch == '}':
                self.pos += 1
                return result
            raise ValueError(
                "Expected ',' or '}' at position %d" % self.pos
            )


def loads(s):
    """Deserialize a JSON-formatted string to a Python object."""
    parser = _Parser(s)
    result = parser.parse_value()
    parser._skip_ws()
    if parser.pos != parser.n:
        raise ValueError(
            "Extra data at position %d" % parser.pos
        )
    return result


def load(fp):
    """Read JSON from a file-like object and deserialize."""
    return loads(fp.read())


# ---------------------------------------------------------------------------
# Invariant probe functions
# ---------------------------------------------------------------------------

def json2_dumps():
    """Invariant: dumps must produce correct JSON for representative values.

    Returns True iff dumps behaves correctly across primitives and containers.
    """
    checks = [
        (dumps(None), "null"),
        (dumps(True), "true"),
        (dumps(False), "false"),
        (dumps(0), "0"),
        (dumps(42), "42"),
        (dumps(-7), "-7"),
        (dumps("hello"), '"hello"'),
        (dumps([]), "[]"),
        (dumps({}), "{}"),
        (dumps([1, 2, 3]), "[1, 2, 3]"),
        (dumps({"a": 1}), '"a": 1'.join(["{", "}"])),
    ]
    for produced, expected in checks:
        if produced != expected:
            return False
    return True


def json2_loads():
    """Invariant: loads must correctly parse a JSON string literal.

    Returns the decoded value of '"value"', which is the Python string "value".
    """
    return loads('"value"')


def json2_round_trip():
    """Invariant: loads(dumps(obj)) == obj for representative objects.

    Returns True iff round-tripping is faithful.
    """
    samples = [
        None,
        True,
        False,
        0,
        1,
        -1,
        42,
        3.5,
        -2.25,
        "",
        "value",
        "with \"quotes\" and \\backslash\\",
        "newline\nand\ttab",
        "unicode: \u00e9 \u4e2d",
        [],
        {},
        [1, 2, 3, 4],
        {"key": "value"},
        {"nested": {"a": [1, 2, {"b": None}]}, "list": [True, False, None]},
        [None, True, False, 0, "x", [1, [2, [3]]], {"k": "v"}],
    ]
    for obj in samples:
        encoded = dumps(obj)
        decoded = loads(encoded)
        if decoded != obj:
            return False
    return True


__all__ = [
    "dumps",
    "loads",
    "dump",
    "load",
    "json2_dumps",
    "json2_loads",
    "json2_round_trip",
]