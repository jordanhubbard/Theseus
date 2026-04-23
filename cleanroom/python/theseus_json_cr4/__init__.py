"""
theseus_json_cr4: Clean-room JSON implementation (no import json).
"""

import re
import math


class JSONDecodeError(ValueError):
    def __init__(self, msg, doc='', pos=0):
        self.msg = msg
        self.doc = doc
        self.pos = pos
        super().__init__(f'{msg}: line {self._lineno(doc, pos)} column {self._colno(doc, pos)} (char {pos})')

    @staticmethod
    def _lineno(doc, pos):
        return doc[:pos].count('\n') + 1

    @staticmethod
    def _colno(doc, pos):
        last_nl = doc[:pos].rfind('\n')
        return pos - last_nl


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_WHITESPACE = frozenset(' \t\n\r')

_ESCAPE_MAP = {
    '"': '"',
    '\\': '\\',
    '/': '/',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
}


def _skip_ws(s, i):
    n = len(s)
    while i < n and s[i] in _WHITESPACE:
        i += 1
    return i


def _parse_value(s, i, object_hook):
    i = _skip_ws(s, i)
    n = len(s)
    if i >= n:
        raise JSONDecodeError('Expecting value', s, i)
    c = s[i]
    if c == '"':
        return _parse_string(s, i)
    elif c == '{':
        return _parse_object(s, i, object_hook)
    elif c == '[':
        return _parse_array(s, i, object_hook)
    elif c == 't':
        if s[i:i+4] == 'true':
            return True, i + 4
        raise JSONDecodeError('Expecting value', s, i)
    elif c == 'f':
        if s[i:i+5] == 'false':
            return False, i + 5
        raise JSONDecodeError('Expecting value', s, i)
    elif c == 'n':
        if s[i:i+4] == 'null':
            return None, i + 4
        raise JSONDecodeError('Expecting value', s, i)
    elif c == '-' or c.isdigit():
        return _parse_number(s, i)
    else:
        raise JSONDecodeError('Expecting value', s, i)


def _parse_string(s, i):
    # i points to opening "
    n = len(s)
    assert s[i] == '"'
    i += 1
    chunks = []
    while i < n:
        c = s[i]
        if c == '"':
            return ''.join(chunks), i + 1
        elif c == '\\':
            i += 1
            if i >= n:
                raise JSONDecodeError('Unterminated string', s, i)
            esc = s[i]
            if esc in _ESCAPE_MAP:
                chunks.append(_ESCAPE_MAP[esc])
                i += 1
            elif esc == 'u':
                # unicode escape
                hex_str = s[i+1:i+5]
                if len(hex_str) < 4:
                    raise JSONDecodeError('Invalid \\uXXXX escape', s, i)
                try:
                    code = int(hex_str, 16)
                except ValueError:
                    raise JSONDecodeError('Invalid \\uXXXX escape', s, i)
                i += 5
                # Handle surrogate pairs
                if 0xD800 <= code <= 0xDBFF:
                    # high surrogate, expect low surrogate
                    if i < n - 1 and s[i] == '\\' and s[i+1] == 'u':
                        hex_str2 = s[i+2:i+6]
                        if len(hex_str2) == 4:
                            try:
                                code2 = int(hex_str2, 16)
                            except ValueError:
                                code2 = 0
                            if 0xDC00 <= code2 <= 0xDFFF:
                                code = 0x10000 + (code - 0xD800) * 0x400 + (code2 - 0xDC00)
                                i += 6
                                chunks.append(chr(code))
                                continue
                chunks.append(chr(code))
            else:
                raise JSONDecodeError(f'Invalid escape character {esc!r}', s, i)
        elif ord(c) < 0x20:
            raise JSONDecodeError('Invalid control character', s, i)
        else:
            # Find next special character
            j = i + 1
            while j < n and s[j] != '"' and s[j] != '\\' and ord(s[j]) >= 0x20:
                j += 1
            chunks.append(s[i:j])
            i = j
    raise JSONDecodeError('Unterminated string', s, i)


def _parse_object(s, i, object_hook):
    assert s[i] == '{'
    i += 1
    n = len(s)
    result = {}
    i = _skip_ws(s, i)
    if i < n and s[i] == '}':
        obj = result
        if object_hook is not None:
            obj = object_hook(result)
        return obj, i + 1
    while i < n:
        i = _skip_ws(s, i)
        if i >= n or s[i] != '"':
            raise JSONDecodeError('Expecting property name enclosed in double quotes', s, i)
        key, i = _parse_string(s, i)
        i = _skip_ws(s, i)
        if i >= n or s[i] != ':':
            raise JSONDecodeError('Expecting \':\' delimiter', s, i)
        i += 1
        value, i = _parse_value(s, i, object_hook)
        result[key] = value
        i = _skip_ws(s, i)
        if i >= n:
            raise JSONDecodeError('Unterminated object', s, i)
        if s[i] == '}':
            obj = result
            if object_hook is not None:
                obj = object_hook(result)
            return obj, i + 1
        elif s[i] == ',':
            i += 1
        else:
            raise JSONDecodeError('Expecting \',\' delimiter or \'}\'', s, i)
    raise JSONDecodeError('Unterminated object', s, i)


def _parse_array(s, i, object_hook):
    assert s[i] == '['
    i += 1
    n = len(s)
    result = []
    i = _skip_ws(s, i)
    if i < n and s[i] == ']':
        return result, i + 1
    while i < n:
        value, i = _parse_value(s, i, object_hook)
        result.append(value)
        i = _skip_ws(s, i)
        if i >= n:
            raise JSONDecodeError('Unterminated array', s, i)
        if s[i] == ']':
            return result, i + 1
        elif s[i] == ',':
            i += 1
        else:
            raise JSONDecodeError('Expecting \',\' delimiter or \']\'', s, i)
    raise JSONDecodeError('Unterminated array', s, i)


_NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][+-]?\d+)?'
)


def _parse_number(s, i):
    m = _NUMBER_RE.match(s, i)
    if not m:
        raise JSONDecodeError('Expecting value', s, i)
    integer_part = m.group(1)
    frac_part = m.group(2)
    exp_part = m.group(3)
    end = m.end()
    if frac_part is None and exp_part is None:
        return int(integer_part), end
    else:
        num_str = integer_part
        if frac_part:
            num_str += frac_part
        if exp_part:
            num_str += exp_part
        return float(num_str), end


def loads(s, object_hook=None):
    """Parse a JSON string and return the Python object."""
    if not isinstance(s, str):
        if isinstance(s, (bytes, bytearray)):
            s = s.decode('utf-8-sig')
        else:
            raise TypeError(f'the JSON object must be str, bytes or bytearray, not {type(s).__name__}')
    value, i = _parse_value(s, 0, object_hook)
    i = _skip_ws(s, i)
    if i < len(s):
        raise JSONDecodeError('Extra data', s, i)
    return value


def load(fp):
    """Load JSON from a file-like object."""
    return loads(fp.read())


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

_CHAR_ESCAPE_MAP = {
    '"': '\\"',
    '\\': '\\\\',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}


def _encode_string(s, ensure_ascii):
    out = ['"']
    for ch in s:
        if ch in _CHAR_ESCAPE_MAP:
            out.append(_CHAR_ESCAPE_MAP[ch])
        elif ord(ch) < 0x20:
            out.append(f'\\u{ord(ch):04x}')
        elif ensure_ascii and ord(ch) > 0x7E:
            cp = ord(ch)
            if cp > 0xFFFF:
                # Encode as surrogate pair
                cp -= 0x10000
                high = 0xD800 + (cp >> 10)
                low = 0xDC00 + (cp & 0x3FF)
                out.append(f'\\u{high:04x}\\u{low:04x}')
            else:
                out.append(f'\\u{cp:04x}')
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _encode_value(obj, ensure_ascii, default, _current_indent_level=0):
    if obj is None:
        return 'null'
    elif obj is True:
        return 'true'
    elif obj is False:
        return 'false'
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f'Out of range float values are not JSON compliant: {obj!r}')
        # Represent float
        return repr(obj)
    elif isinstance(obj, str):
        return _encode_string(obj, ensure_ascii)
    elif isinstance(obj, (list, tuple)):
        if not obj:
            return '[]'
        items = [_encode_value(item, ensure_ascii, default) for item in obj]
        return '[' + ', '.join(items) + ']'
    elif isinstance(obj, dict):
        if not obj:
            return '{}'
        pairs = []
        for k, v in obj.items():
            if not isinstance(k, str):
                if isinstance(k, bool):
                    k = 'true' if k else 'false'
                elif isinstance(k, int):
                    k = str(k)
                elif isinstance(k, float):
                    k = repr(k)
                elif k is None:
                    k = 'null'
                else:
                    raise TypeError(f'keys must be strings, not {type(k).__name__}')
            pairs.append(_encode_string(k, ensure_ascii) + ': ' + _encode_value(v, ensure_ascii, default))
        return '{' + ', '.join(pairs) + '}'
    else:
        if default is not None:
            transformed = default(obj)
            return _encode_value(transformed, ensure_ascii, default)
        raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


def dumps(obj, ensure_ascii=True, default=None):
    """Serialize obj to a JSON formatted string."""
    return _encode_value(obj, ensure_ascii, default)


def dump(obj, fp, ensure_ascii=True, default=None):
    """Serialize obj as a JSON formatted stream to fp."""
    fp.write(dumps(obj, ensure_ascii=ensure_ascii, default=default))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def json4_object_hook():
    """loads('{"a":1}', object_hook=lambda d: d['a']) == 1"""
    return loads('{"a":1}', object_hook=lambda d: d['a'])


def json4_ensure_ascii_false():
    """'é' in dumps({'x': 'é'}, ensure_ascii=False)"""
    return 'é' in dumps({'x': 'é'}, ensure_ascii=False)


def json4_default_hook():
    """dumps({'x': set()}, default=lambda o: list(o)) works"""
    result = dumps({'x': set()}, default=lambda o: list(o))
    return isinstance(result, str)


__all__ = [
    'loads',
    'dumps',
    'load',
    'dump',
    'JSONDecodeError',
    'json4_object_hook',
    'json4_ensure_ascii_false',
    'json4_default_hook',
]