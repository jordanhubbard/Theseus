"""
theseus_json_cr3 - Clean-room JSON utilities implementation
No imports of json, simplejson, or any third-party JSON library.
"""

import re
import math


# ─────────────────────────────────────────────
#  DECODER
# ─────────────────────────────────────────────

class JSONDecodeError(ValueError):
    pass


def _parse_string(s, pos):
    """Parse a JSON string starting at pos (which should point to the opening quote).
    Returns (string_value, new_pos)."""
    assert s[pos] == '"'
    pos += 1
    chunks = []
    while pos < len(s):
        ch = s[pos]
        if ch == '"':
            return ''.join(chunks), pos + 1
        elif ch == '\\':
            pos += 1
            if pos >= len(s):
                raise JSONDecodeError("Unterminated escape sequence")
            esc = s[pos]
            if esc == '"':
                chunks.append('"')
            elif esc == '\\':
                chunks.append('\\')
            elif esc == '/':
                chunks.append('/')
            elif esc == 'b':
                chunks.append('\b')
            elif esc == 'f':
                chunks.append('\f')
            elif esc == 'n':
                chunks.append('\n')
            elif esc == 'r':
                chunks.append('\r')
            elif esc == 't':
                chunks.append('\t')
            elif esc == 'u':
                hex_str = s[pos+1:pos+5]
                if len(hex_str) < 4:
                    raise JSONDecodeError("Invalid \\uXXXX escape")
                try:
                    code = int(hex_str, 16)
                except ValueError:
                    raise JSONDecodeError("Invalid \\uXXXX escape: " + hex_str)
                # Handle surrogate pairs
                char = chr(code)
                pos += 4
                # Check for surrogate pair
                if 0xD800 <= code <= 0xDBFF:
                    # High surrogate, look for low surrogate
                    if pos + 1 < len(s) and s[pos+1] == '\\' and pos + 2 < len(s) and s[pos+2] == 'u':
                        hex_str2 = s[pos+3:pos+7]
                        if len(hex_str2) == 4:
                            try:
                                code2 = int(hex_str2, 16)
                            except ValueError:
                                code2 = -1
                            if 0xDC00 <= code2 <= 0xDFFF:
                                full_code = 0x10000 + (code - 0xD800) * 0x400 + (code2 - 0xDC00)
                                char = chr(full_code)
                                pos += 6
                chunks.append(char)
            else:
                raise JSONDecodeError("Invalid escape character: \\" + esc)
            pos += 1
        else:
            chunks.append(ch)
            pos += 1
    raise JSONDecodeError("Unterminated string")


def _skip_whitespace(s, pos):
    while pos < len(s) and s[pos] in ' \t\n\r':
        pos += 1
    return pos


def _parse_value(s, pos):
    """Parse a JSON value starting at pos. Returns (value, new_pos)."""
    pos = _skip_whitespace(s, pos)
    if pos >= len(s):
        raise JSONDecodeError("Unexpected end of input")
    ch = s[pos]

    if ch == '"':
        return _parse_string(s, pos)
    elif ch == '{':
        return _parse_object(s, pos)
    elif ch == '[':
        return _parse_array(s, pos)
    elif ch == 't':
        if s[pos:pos+4] == 'true':
            return True, pos + 4
        raise JSONDecodeError("Invalid token at position " + str(pos))
    elif ch == 'f':
        if s[pos:pos+5] == 'false':
            return False, pos + 5
        raise JSONDecodeError("Invalid token at position " + str(pos))
    elif ch == 'n':
        if s[pos:pos+4] == 'null':
            return None, pos + 4
        raise JSONDecodeError("Invalid token at position " + str(pos))
    elif ch == '-' or ch.isdigit():
        return _parse_number(s, pos)
    else:
        raise JSONDecodeError("Unexpected character: " + repr(ch) + " at position " + str(pos))


def _parse_number(s, pos):
    """Parse a JSON number. Returns (number, new_pos)."""
    start = pos
    if pos < len(s) and s[pos] == '-':
        pos += 1
    if pos >= len(s):
        raise JSONDecodeError("Invalid number")
    if s[pos] == '0':
        pos += 1
    elif s[pos].isdigit():
        while pos < len(s) and s[pos].isdigit():
            pos += 1
    else:
        raise JSONDecodeError("Invalid number at position " + str(pos))

    is_float = False
    if pos < len(s) and s[pos] == '.':
        is_float = True
        pos += 1
        if pos >= len(s) or not s[pos].isdigit():
            raise JSONDecodeError("Invalid number: expected digit after decimal point")
        while pos < len(s) and s[pos].isdigit():
            pos += 1

    if pos < len(s) and s[pos] in 'eE':
        is_float = True
        pos += 1
        if pos < len(s) and s[pos] in '+-':
            pos += 1
        if pos >= len(s) or not s[pos].isdigit():
            raise JSONDecodeError("Invalid number: expected digit in exponent")
        while pos < len(s) and s[pos].isdigit():
            pos += 1

    num_str = s[start:pos]
    try:
        if is_float:
            return float(num_str), pos
        else:
            return int(num_str), pos
    except ValueError:
        raise JSONDecodeError("Invalid number: " + num_str)


def _parse_object(s, pos):
    """Parse a JSON object. Returns (dict, new_pos)."""
    assert s[pos] == '{'
    pos += 1
    result = {}
    pos = _skip_whitespace(s, pos)
    if pos < len(s) and s[pos] == '}':
        return result, pos + 1

    while True:
        pos = _skip_whitespace(s, pos)
        if pos >= len(s) or s[pos] != '"':
            raise JSONDecodeError("Expected string key in object at position " + str(pos))
        key, pos = _parse_string(s, pos)
        pos = _skip_whitespace(s, pos)
        if pos >= len(s) or s[pos] != ':':
            raise JSONDecodeError("Expected ':' after key in object at position " + str(pos))
        pos += 1
        value, pos = _parse_value(s, pos)
        result[key] = value
        pos = _skip_whitespace(s, pos)
        if pos >= len(s):
            raise JSONDecodeError("Unterminated object")
        if s[pos] == '}':
            return result, pos + 1
        elif s[pos] == ',':
            pos += 1
        else:
            raise JSONDecodeError("Expected ',' or '}' in object at position " + str(pos))


def _parse_array(s, pos):
    """Parse a JSON array. Returns (list, new_pos)."""
    assert s[pos] == '['
    pos += 1
    result = []
    pos = _skip_whitespace(s, pos)
    if pos < len(s) and s[pos] == ']':
        return result, pos + 1

    while True:
        value, pos = _parse_value(s, pos)
        result.append(value)
        pos = _skip_whitespace(s, pos)
        if pos >= len(s):
            raise JSONDecodeError("Unterminated array")
        if s[pos] == ']':
            return result, pos + 1
        elif s[pos] == ',':
            pos += 1
        else:
            raise JSONDecodeError("Expected ',' or ']' in array at position " + str(pos))


def loads(s):
    """Deserialize s (a str) to a Python object."""
    if not isinstance(s, str):
        raise TypeError("the JSON object must be str, not " + type(s).__name__)
    value, pos = _parse_value(s, 0)
    pos = _skip_whitespace(s, pos)
    if pos != len(s):
        raise JSONDecodeError("Extra data after JSON value at position " + str(pos))
    return value


class JSONDecoder:
    """JSON decoder class."""

    def __init__(self, *, object_hook=None, parse_float=None, parse_int=None,
                 parse_constant=None, strict=True, object_pairs_hook=None):
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.strict = strict
        self.object_pairs_hook = object_pairs_hook

    def decode(self, s):
        """Decode a JSON string and return the Python object."""
        return loads(s)

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from s beginning at index idx."""
        value, pos = _parse_value(s, idx)
        return value, pos


# ─────────────────────────────────────────────
#  ENCODER
# ─────────────────────────────────────────────

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
    """Encode a Python string as a JSON string."""
    result = ['"']
    for ch in s:
        if ch in _ESCAPE_MAP:
            result.append(_ESCAPE_MAP[ch])
        elif ord(ch) < 0x20:
            result.append('\\u{:04x}'.format(ord(ch)))
        else:
            result.append(ch)
    result.append('"')
    return ''.join(result)


def _encode_value(obj, sort_keys=False, indent=None, current_indent=0,
                  separators=None, ensure_ascii=True):
    """Encode a Python object as a JSON string."""
    if separators is not None:
        item_sep, key_sep = separators
    else:
        if indent is not None:
            item_sep = ','
            key_sep = ': '
        else:
            item_sep = ', '
            key_sep = ': '

    if obj is None:
        return 'null'
    elif obj is True:
        return 'true'
    elif obj is False:
        return 'false'
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, float):
        if math.isnan(obj):
            raise ValueError("Out of range float values are not JSON compliant: nan")
        if math.isinf(obj):
            raise ValueError("Out of range float values are not JSON compliant: inf")
        # Represent float
        r = repr(obj)
        return r
    elif isinstance(obj, str):
        encoded = _encode_string(obj)
        if ensure_ascii:
            # Replace non-ASCII characters with \uXXXX
            result = []
            for ch in encoded[1:-1]:  # strip quotes
                if ord(ch) > 127:
                    cp = ord(ch)
                    if cp > 0xFFFF:
                        # Encode as surrogate pair
                        cp -= 0x10000
                        high = 0xD800 + (cp >> 10)
                        low = 0xDC00 + (cp & 0x3FF)
                        result.append('\\u{:04x}\\u{:04x}'.format(high, low))
                    else:
                        result.append('\\u{:04x}'.format(cp))
                else:
                    result.append(ch)
            return '"' + ''.join(result) + '"'
        return encoded
    elif isinstance(obj, (list, tuple)):
        if not obj:
            return '[]'
        if indent is not None:
            next_indent = current_indent + indent
            indent_str = ' ' * next_indent
            close_indent_str = ' ' * current_indent
            items = []
            for item in obj:
                items.append(indent_str + _encode_value(
                    item, sort_keys=sort_keys, indent=indent,
                    current_indent=next_indent, separators=separators,
                    ensure_ascii=ensure_ascii))
            return '[\n' + (item_sep + '\n').join(items) + '\n' + close_indent_str + ']'
        else:
            items = [_encode_value(item, sort_keys=sort_keys, indent=indent,
                                   current_indent=current_indent, separators=separators,
                                   ensure_ascii=ensure_ascii)
                     for item in obj]
            return '[' + item_sep.join(items) + ']'
    elif isinstance(obj, dict):
        if not obj:
            return '{}'
        keys = list(obj.keys())
        if sort_keys:
            keys = sorted(keys, key=lambda k: str(k))
        if indent is not None:
            next_indent = current_indent + indent
            indent_str = ' ' * next_indent
            close_indent_str = ' ' * current_indent
            items = []
            for k in keys:
                key_encoded = _encode_value(k, sort_keys=sort_keys, indent=indent,
                                            current_indent=next_indent, separators=separators,
                                            ensure_ascii=ensure_ascii)
                val_encoded = _encode_value(obj[k], sort_keys=sort_keys, indent=indent,
                                            current_indent=next_indent, separators=separators,
                                            ensure_ascii=ensure_ascii)
                items.append(indent_str + key_encoded + key_sep + val_encoded)
            return '{\n' + (item_sep + '\n').join(items) + '\n' + close_indent_str + '}'
        else:
            items = []
            for k in keys:
                key_encoded = _encode_value(k, sort_keys=sort_keys, indent=indent,
                                            current_indent=current_indent, separators=separators,
                                            ensure_ascii=ensure_ascii)
                val_encoded = _encode_value(obj[k], sort_keys=sort_keys, indent=indent,
                                            current_indent=current_indent, separators=separators,
                                            ensure_ascii=ensure_ascii)
                items.append(key_encoded + key_sep + val_encoded)
            return '{' + item_sep.join(items) + '}'
    else:
        raise TypeError("Object of type " + type(obj).__name__ + " is not JSON serializable")


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=False, cls=None, indent=None, separators=None,
          default=None, sort_keys=False, **kw):
    """Serialize obj to a JSON formatted string."""
    return _encode_value(obj, sort_keys=sort_keys, indent=indent,
                         separators=separators, ensure_ascii=ensure_ascii)


class JSONEncoder:
    """JSON encoder class."""

    def __init__(self, *, skipkeys=False, ensure_ascii=True, check_circular=True,
                 allow_nan=False, sort_keys=False, indent=None, separators=None,
                 default=None):
        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.separators = separators
        self.default = default

    def default(self, obj):
        raise TypeError("Object of type " + type(obj).__name__ + " is not JSON serializable")

    def encode(self, obj):
        """Return a JSON string representation of a Python data structure."""
        return _encode_value(obj, sort_keys=self.sort_keys, indent=self.indent,
                             separators=self.separators, ensure_ascii=self.ensure_ascii)

    def iterencode(self, obj):
        """Encode the given object and yield each string representation as available."""
        # For simplicity, yield the whole encoded string at once
        yield self.encode(obj)


# ─────────────────────────────────────────────
#  TEST / INVARIANT FUNCTIONS
# ─────────────────────────────────────────────

def json3_decoder():
    """Test that JSONDecoder().decode('{"a":1}') == {'a': 1}."""
    result = JSONDecoder().decode('{"a":1}')
    return result == {'a': 1}


def json3_encoder_sort_keys():
    """Test that JSONEncoder(sort_keys=True).encode({'b':2,'a':1}) starts with '{"a"'."""
    result = JSONEncoder(sort_keys=True).encode({'b': 2, 'a': 1})
    return result.startswith('{"a"')


def json3_encoder_indent():
    """Test that JSONEncoder(indent=2).encode({'x':1}) contains a newline."""
    result = JSONEncoder(indent=2).encode({'x': 1})
    return '\n' in result


__all__ = [
    'JSONDecoder',
    'JSONEncoder',
    'JSONDecodeError',
    'loads',
    'dumps',
    'json3_decoder',
    'json3_encoder_sort_keys',
    'json3_encoder_indent',
]