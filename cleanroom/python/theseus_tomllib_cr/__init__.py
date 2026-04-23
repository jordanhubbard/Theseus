"""
theseus_tomllib_cr — Clean-room tomllib module.
No import of the standard `tomllib` module.
Pure-Python TOML parser (TOML v1.0).
"""

import re as _re
import io as _io
import datetime as _dt
from typing import Any


class TOMLDecodeError(ValueError):
    """Raised when a TOML document cannot be parsed."""
    pass


# ---------------------------------------------------------------------------
# Tokenizer helpers
# ---------------------------------------------------------------------------

_BARE_KEY_RE = _re.compile(r'[A-Za-z0-9_-]+')
_INT_RE = _re.compile(r'[+-]?(?:0|[1-9](?:[0-9_]*[0-9])?)')
_FLOAT_RE = _re.compile(r'[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|[+-]?(?:inf|nan)')
_DATE_RE = _re.compile(r'(\d{4})-(\d{2})-(\d{2})')
_TIME_RE = _re.compile(r'(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(?:Z|([+-]\d{2}:\d{2}))?')
_DATETIME_RE = _re.compile(
    r'(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(?:Z|([+-]\d{2}:\d{2}))?'
)


def _skip_whitespace_and_newlines(src, pos):
    while pos < len(src) and src[pos] in ' \t\r\n':
        pos += 1
    return pos


def _skip_whitespace(src, pos):
    while pos < len(src) and src[pos] in ' \t':
        pos += 1
    return pos


def _skip_comment(src, pos):
    if pos < len(src) and src[pos] == '#':
        while pos < len(src) and src[pos] != '\n':
            pos += 1
    return pos


def _parse_basic_string(src, pos):
    """Parse a basic (double-quoted) string. pos points after opening quote."""
    result = []
    while pos < len(src):
        c = src[pos]
        if c == '"':
            return ''.join(result), pos + 1
        if c == '\\':
            pos += 1
            if pos >= len(src):
                raise TOMLDecodeError("Unexpected end in string escape")
            esc = src[pos]
            if esc == 'b':
                result.append('\b')
            elif esc == 't':
                result.append('\t')
            elif esc == 'n':
                result.append('\n')
            elif esc == 'f':
                result.append('\f')
            elif esc == 'r':
                result.append('\r')
            elif esc == '"':
                result.append('"')
            elif esc == '\\':
                result.append('\\')
            elif esc == 'u':
                hex_str = src[pos+1:pos+5]
                result.append(chr(int(hex_str, 16)))
                pos += 4
            elif esc == 'U':
                hex_str = src[pos+1:pos+9]
                result.append(chr(int(hex_str, 16)))
                pos += 8
            else:
                raise TOMLDecodeError(f"Invalid escape: \\{esc}")
        else:
            result.append(c)
        pos += 1
    raise TOMLDecodeError("Unterminated basic string")


def _parse_literal_string(src, pos):
    """Parse a literal (single-quoted) string. pos points after opening quote."""
    end = src.find("'", pos)
    if end == -1:
        raise TOMLDecodeError("Unterminated literal string")
    return src[pos:end], end + 1


def _parse_multiline_basic_string(src, pos):
    """Parse a multiline basic string. pos points after opening triple-quote."""
    if pos < len(src) and src[pos] == '\n':
        pos += 1
    result = []
    while pos < len(src):
        if src[pos:pos+3] == '"""':
            return ''.join(result), pos + 3
        if src[pos] == '\\':
            pos += 1
            if pos < len(src) and src[pos] in ' \t\r\n':
                while pos < len(src) and src[pos] in ' \t\r\n':
                    pos += 1
                continue
            if pos >= len(src):
                raise TOMLDecodeError("Unexpected end in multiline string")
            esc = src[pos]
            if esc == 'n':
                result.append('\n')
            elif esc == 't':
                result.append('\t')
            elif esc == 'r':
                result.append('\r')
            elif esc == '"':
                result.append('"')
            elif esc == '\\':
                result.append('\\')
            else:
                result.append(esc)
        else:
            result.append(src[pos])
        pos += 1
    raise TOMLDecodeError("Unterminated multiline basic string")


def _parse_multiline_literal_string(src, pos):
    """Parse a multiline literal string. pos points after opening triple-quote."""
    if pos < len(src) and src[pos] == '\n':
        pos += 1
    end = src.find("'''", pos)
    if end == -1:
        raise TOMLDecodeError("Unterminated multiline literal string")
    return src[pos:end], end + 3


def _parse_string(src, pos):
    """Parse any string type, return (value, new_pos)."""
    if src[pos:pos+3] == '"""':
        return _parse_multiline_basic_string(src, pos + 3)
    if src[pos:pos+3] == "'''":
        return _parse_multiline_literal_string(src, pos + 3)
    if src[pos] == '"':
        return _parse_basic_string(src, pos + 1)
    if src[pos] == "'":
        return _parse_literal_string(src, pos + 1)
    raise TOMLDecodeError(f"Expected string at pos {pos}")


def _parse_number(src, pos):
    """Parse integer or float, return (value, new_pos)."""
    # Check for special floats
    for special in ('inf', '+inf', '-inf', 'nan', '+nan', '-nan'):
        if src[pos:pos+len(special)] == special:
            val = float(special.lstrip('+'))
            return val, pos + len(special)

    # Hex, octal, binary integers
    if src[pos:pos+2] == '0x':
        m = _re.match(r'0x([0-9A-Fa-f_]+)', src[pos:])
        if m:
            return int(m.group(1).replace('_', ''), 16), pos + len(m.group(0))
    if src[pos:pos+2] == '0o':
        m = _re.match(r'0o([0-7_]+)', src[pos:])
        if m:
            return int(m.group(1).replace('_', ''), 8), pos + len(m.group(0))
    if src[pos:pos+2] == '0b':
        m = _re.match(r'0b([01_]+)', src[pos:])
        if m:
            return int(m.group(1).replace('_', ''), 2), pos + len(m.group(0))

    # Float or integer
    m = _re.match(r'[+-]?(?:0|[1-9][0-9_]*)(?:\.[0-9_]+)?(?:[eE][+-]?[0-9_]+)?', src[pos:])
    if not m or not m.group(0):
        raise TOMLDecodeError(f"Invalid number at pos {pos}")
    s = m.group(0).replace('_', '')
    end = pos + len(m.group(0))
    if '.' in s or 'e' in s or 'E' in s:
        return float(s), end
    return int(s), end


def _parse_datetime(src, pos):
    """Try to parse a datetime/date/time value."""
    m = _DATETIME_RE.match(src, pos)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hour, minute, sec = int(m.group(4)), int(m.group(5)), int(m.group(6))
        frac = m.group(7) or ''
        microsec = int((frac + '000000')[:6]) if frac else 0
        tz_str = m.group(8)
        if tz_str == 'Z' or src[m.start(7) + len(frac) if frac else m.end(6)] == 'Z':
            tz = _dt.timezone.utc
        elif tz_str:
            sign = 1 if tz_str[0] == '+' else -1
            th, tm = int(tz_str[1:3]), int(tz_str[4:6])
            tz = _dt.timezone(_dt.timedelta(hours=sign*th, minutes=sign*tm))
        else:
            tz = None
        dt = _dt.datetime(year, month, day, hour, minute, sec, microsec, tz)
        return dt, m.end()

    m = _DATE_RE.match(src, pos)
    if m:
        next_char = src[m.end()] if m.end() < len(src) else ''
        if next_char not in 'T ':
            return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m.end()

    return None, pos


def _parse_value(src, pos):
    """Parse a TOML value, return (value, new_pos)."""
    pos = _skip_whitespace(src, pos)
    if pos >= len(src):
        raise TOMLDecodeError("Unexpected end of input")

    c = src[pos]

    # String
    if c in ('"', "'"):
        return _parse_string(src, pos)

    # Boolean
    if src[pos:pos+4] == 'true':
        return True, pos + 4
    if src[pos:pos+5] == 'false':
        return False, pos + 5

    # Array
    if c == '[':
        return _parse_array(src, pos + 1)

    # Inline table
    if c == '{':
        return _parse_inline_table(src, pos + 1)

    # Datetime (try before number)
    dt_val, new_pos = _parse_datetime(src, pos)
    if dt_val is not None:
        return dt_val, new_pos

    # Number
    if c in '0123456789+-' or src[pos:pos+3] in ('inf', 'nan'):
        return _parse_number(src, pos)

    raise TOMLDecodeError(f"Unexpected character {c!r} at pos {pos}")


def _parse_array(src, pos):
    """Parse an array. pos points after opening '['."""
    result = []
    while True:
        pos = _skip_whitespace_and_newlines(src, pos)
        pos = _skip_comment(src, pos)
        pos = _skip_whitespace_and_newlines(src, pos)
        if pos >= len(src):
            raise TOMLDecodeError("Unterminated array")
        if src[pos] == ']':
            return result, pos + 1
        val, pos = _parse_value(src, pos)
        result.append(val)
        pos = _skip_whitespace_and_newlines(src, pos)
        pos = _skip_comment(src, pos)
        pos = _skip_whitespace_and_newlines(src, pos)
        if pos < len(src) and src[pos] == ',':
            pos += 1
        elif pos < len(src) and src[pos] == ']':
            return result, pos + 1
        else:
            if pos >= len(src):
                raise TOMLDecodeError("Unterminated array")


def _parse_inline_table(src, pos):
    """Parse an inline table. pos points after opening '{'."""
    result = {}
    first = True
    while True:
        pos = _skip_whitespace(src, pos)
        if pos >= len(src):
            raise TOMLDecodeError("Unterminated inline table")
        if src[pos] == '}':
            return result, pos + 1
        if not first:
            if src[pos] != ',':
                raise TOMLDecodeError(f"Expected ',' in inline table at pos {pos}")
            pos += 1
            pos = _skip_whitespace(src, pos)
        first = False
        key, pos = _parse_key(src, pos)
        pos = _skip_whitespace(src, pos)
        if pos >= len(src) or src[pos] != '=':
            raise TOMLDecodeError(f"Expected '=' after key in inline table")
        pos += 1
        val, pos = _parse_value(src, pos)
        _set_nested(result, key, val)
    return result, pos


def _parse_key(src, pos):
    """Parse a key (possibly dotted). Returns (list_of_parts, new_pos)."""
    parts = []
    while True:
        pos = _skip_whitespace(src, pos)
        if pos >= len(src):
            raise TOMLDecodeError("Unexpected end while parsing key")
        c = src[pos]
        if c == '"' or c == "'":
            part, pos = _parse_string(src, pos)
        else:
            m = _BARE_KEY_RE.match(src, pos)
            if not m:
                raise TOMLDecodeError(f"Invalid key character {c!r} at pos {pos}")
            part = m.group(0)
            pos = m.end()
        parts.append(part)
        pos = _skip_whitespace(src, pos)
        if pos < len(src) and src[pos] == '.':
            pos += 1
        else:
            break
    return parts, pos


def _set_nested(table, keys, value):
    """Set a nested key in table dict."""
    for k in keys[:-1]:
        if k not in table:
            table[k] = {}
        elif not isinstance(table[k], dict):
            raise TOMLDecodeError(f"Key {k!r} already defined as non-table")
        table = table[k]
    last = keys[-1]
    if last in table:
        raise TOMLDecodeError(f"Duplicate key {last!r}")
    table[last] = value


def _get_or_create_table(root, keys):
    """Navigate to a nested table, creating dicts along the way."""
    table = root
    for k in keys:
        if k not in table:
            table[k] = {}
        val = table[k]
        if isinstance(val, list):
            table = val[-1]
        elif isinstance(val, dict):
            table = val
        else:
            raise TOMLDecodeError(f"Key {k!r} is not a table")
    return table


def _parse_document(src):
    """Parse a full TOML document string."""
    root = {}
    current_table = root
    current_path = []
    array_of_tables_paths = set()

    pos = 0
    while pos < len(src):
        pos = _skip_whitespace(src, pos)
        if pos >= len(src):
            break

        c = src[pos]

        # Comment
        if c == '#':
            pos = _skip_comment(src, pos)
            continue

        # Newline
        if c in '\r\n':
            if c == '\r' and pos + 1 < len(src) and src[pos+1] == '\n':
                pos += 2
            else:
                pos += 1
            continue

        # Array of tables [[...]]
        if src[pos:pos+2] == '[[':
            pos += 2
            key, pos = _parse_key(src, pos)
            pos = _skip_whitespace(src, pos)
            if src[pos:pos+2] != ']]':
                raise TOMLDecodeError("Expected ']]' after array-of-tables key")
            pos += 2
            path_key = tuple(key)
            array_of_tables_paths.add(path_key)
            # Navigate to parent and append new table
            parent = _get_or_create_table(root, key[:-1])
            last = key[-1]
            if last not in parent:
                parent[last] = []
            if not isinstance(parent[last], list):
                raise TOMLDecodeError(f"Key {last!r} is not an array of tables")
            new_table = {}
            parent[last].append(new_table)
            current_table = new_table
            current_path = key
            continue

        # Table header [...]
        if c == '[':
            pos += 1
            key, pos = _parse_key(src, pos)
            pos = _skip_whitespace(src, pos)
            if pos >= len(src) or src[pos] != ']':
                raise TOMLDecodeError("Expected ']' after table key")
            pos += 1
            current_table = _get_or_create_table(root, key)
            current_path = key
            continue

        # Key-value pair
        key, pos = _parse_key(src, pos)
        pos = _skip_whitespace(src, pos)
        if pos >= len(src) or src[pos] != '=':
            raise TOMLDecodeError(f"Expected '=' after key at pos {pos}")
        pos += 1
        val, pos = _parse_value(src, pos)
        pos = _skip_whitespace(src, pos)
        if pos < len(src) and src[pos] == '#':
            pos = _skip_comment(src, pos)
        if pos < len(src) and src[pos] not in '\r\n':
            raise TOMLDecodeError(f"Expected newline after value at pos {pos}")
        _set_nested(current_table, key, val)

    return root


def loads(s: str) -> dict:
    """Parse a TOML string, return a dict."""
    if not isinstance(s, str):
        raise TypeError(f"Expected str, got {type(s).__name__}")
    try:
        return _parse_document(s)
    except TOMLDecodeError:
        raise
    except Exception as e:
        raise TOMLDecodeError(str(e)) from e


def load(fp) -> dict:
    """Parse a TOML file-like object (binary mode), return a dict."""
    b = fp.read()
    if isinstance(b, (bytes, bytearray)):
        s = b.decode('utf-8')
    else:
        s = b
    return loads(s)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def tomllib2_loads():
    """loads() parses a TOML string; returns True."""
    result = loads('[section]\nkey = "value"\nnum = 42\n')
    return (isinstance(result, dict) and
            result.get('section', {}).get('key') == 'value' and
            result.get('section', {}).get('num') == 42)


def tomllib2_load():
    """load() parses a TOML file; returns True."""
    import io as _io2
    data = b'[config]\nenabled = true\ncount = 7\n'
    result = load(_io2.BytesIO(data))
    return (isinstance(result, dict) and
            result.get('config', {}).get('enabled') is True and
            result.get('config', {}).get('count') == 7)


def tomllib2_error():
    """TOMLDecodeError exists as a ValueError subclass; returns True."""
    return (issubclass(TOMLDecodeError, ValueError) and
            TOMLDecodeError.__name__ == 'TOMLDecodeError')


__all__ = [
    'loads', 'load', 'TOMLDecodeError',
    'tomllib2_loads', 'tomllib2_load', 'tomllib2_error',
]
