"""
theseus_json_cr5 — Clean-room JSON implementation (no import json).
Exports: loads, dumps, load, dump, JSONDecodeError, JSONEncoder, JSONDecoder
"""

import re
import math


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class JSONDecodeError(ValueError):
    """Raised when JSON input is malformed."""
    def __init__(self, msg, doc="", pos=0):
        self.msg = msg
        self.doc = doc
        self.pos = pos
        errmsg = f"{msg}: line {self._lineno(doc, pos)} column {self._colno(doc, pos)} (char {pos})"
        super().__init__(errmsg)

    @staticmethod
    def _lineno(doc, pos):
        return doc[:pos].count('\n') + 1

    @staticmethod
    def _colno(doc, pos):
        last_nl = doc[:pos].rfind('\n')
        return pos - last_nl


# ---------------------------------------------------------------------------
# Parser (loads)
# ---------------------------------------------------------------------------

_WHITESPACE = re.compile(r'[ \t\n\r]*', re.MULTILINE)
_NUMBER = re.compile(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?')
_STRING_CHUNK = re.compile(r'[^"\\]+')
_ESCAPE_MAP = {
    '"': '"', '\\': '\\', '/': '/', 'b': '\b',
    'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
}


def _skip_ws(s, idx):
    m = _WHITESPACE.match(s, idx)
    return m.end() if m else idx


def _parse_string(s, idx, end):
    # idx points to the opening quote
    if idx >= end or s[idx] != '"':
        raise JSONDecodeError("Expecting '\"'", s, idx)
    idx += 1  # skip opening quote
    chunks = []
    while idx < end:
        m = _STRING_CHUNK.match(s, idx)
        if m:
            chunks.append(m.group())
            idx = m.end()
        c = s[idx] if idx < end else ''
        if c == '"':
            idx += 1
            return ''.join(chunks), idx
        if c != '\\':
            raise JSONDecodeError("Invalid character in string", s, idx)
        # escape sequence
        idx += 1
        if idx >= end:
            raise JSONDecodeError("Unterminated string escape", s, idx)
        esc = s[idx]
        if esc in _ESCAPE_MAP:
            chunks.append(_ESCAPE_MAP[esc])
            idx += 1
        elif esc == 'u':
            # unicode escape
            if idx + 4 >= end:
                raise JSONDecodeError("Invalid \\uXXXX escape", s, idx)
            hex_str = s[idx+1:idx+5]
            try:
                codepoint = int(hex_str, 16)
            except ValueError:
                raise JSONDecodeError("Invalid \\uXXXX escape", s, idx)
            chunks.append(chr(codepoint))
            idx += 5
        else:
            raise JSONDecodeError(f"Invalid escape character {esc!r}", s, idx)
    raise JSONDecodeError("Unterminated string", s, idx)


def _parse_value(s, idx, end):
    idx = _skip_ws(s, idx)
    if idx >= end:
        raise JSONDecodeError("Expecting value", s, idx)
    c = s[idx]

    if c == '"':
        return _parse_string(s, idx, end)
    if c == '{':
        return _parse_object(s, idx, end)
    if c == '[':
        return _parse_array(s, idx, end)
    if s[idx:idx+4] == 'true':
        return True, idx + 4
    if s[idx:idx+5] == 'false':
        return False, idx + 5
    if s[idx:idx+4] == 'null':
        return None, idx + 4
    # number
    m = _NUMBER.match(s, idx)
    if m:
        num_str = m.group()
        if '.' in num_str or 'e' in num_str or 'E' in num_str:
            return float(num_str), m.end()
        else:
            return int(num_str), m.end()
    raise JSONDecodeError("Expecting value", s, idx)


def _parse_object(s, idx, end):
    # idx points to '{'
    idx += 1
    result = {}
    idx = _skip_ws(s, idx)
    if idx < end and s[idx] == '}':
        return result, idx + 1
    while idx < end:
        idx = _skip_ws(s, idx)
        if idx >= end or s[idx] != '"':
            raise JSONDecodeError("Expecting property name enclosed in double quotes", s, idx)
        key, idx = _parse_string(s, idx, end)
        idx = _skip_ws(s, idx)
        if idx >= end or s[idx] != ':':
            raise JSONDecodeError("Expecting ':' delimiter", s, idx)
        idx += 1
        value, idx = _parse_value(s, idx, end)
        result[key] = value
        idx = _skip_ws(s, idx)
        if idx >= end:
            raise JSONDecodeError("Unterminated object", s, idx)
        if s[idx] == '}':
            return result, idx + 1
        if s[idx] != ',':
            raise JSONDecodeError("Expecting ',' delimiter or '}'", s, idx)
        idx += 1
    raise JSONDecodeError("Unterminated object", s, idx)


def _parse_array(s, idx, end):
    # idx points to '['
    idx += 1
    result = []
    idx = _skip_ws(s, idx)
    if idx < end and s[idx] == ']':
        return result, idx + 1
    while idx < end:
        value, idx = _parse_value(s, idx, end)
        result.append(value)
        idx = _skip_ws(s, idx)
        if idx >= end:
            raise JSONDecodeError("Unterminated array", s, idx)
        if s[idx] == ']':
            return result, idx + 1
        if s[idx] != ',':
            raise JSONDecodeError("Expecting ',' delimiter or ']'", s, idx)
        idx += 1
    raise JSONDecodeError("Unterminated array", s, idx)


def loads(s, *, cls=None, object_hook=None, parse_float=None,
          parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    """Deserialize s (a str) to a Python object."""
    if not isinstance(s, str):
        raise TypeError(f"the JSON object must be str, not {type(s).__name__!r}")
    end = len(s)
    try:
        value, idx = _parse_value(s, 0, end)
    except JSONDecodeError:
        raise
    except Exception as e:
        raise JSONDecodeError(str(e), s, 0) from e
    idx = _skip_ws(s, idx)
    if idx != end:
        raise JSONDecodeError("Extra data", s, idx)
    if object_hook is not None and isinstance(value, dict):
        value = object_hook(value)
    return value


def load(fp, **kw):
    """Deserialize fp (a file-like object) to a Python object."""
    return loads(fp.read(), **kw)


# ---------------------------------------------------------------------------
# Serializer (dumps)
# ---------------------------------------------------------------------------

def _encode_string(s):
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif ch == '\b':
            out.append('\\b')
        elif ch == '\f':
            out.append('\\f')
        elif ord(ch) < 0x20:
            out.append(f'\\u{ord(ch):04x}')
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _encode_value(obj, sort_keys=False, indent=None, _current_indent=0,
                  separators=None, default=None):
    if separators is not None:
        item_sep, key_sep = separators
    else:
        if indent is not None:
            item_sep, key_sep = ',', ': '
        else:
            item_sep, key_sep = ', ', ': '

    if obj is None:
        return 'null'
    if obj is True:
        return 'true'
    if obj is False:
        return 'false'
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(f"Out of range float values are not JSON compliant: {obj!r}")
        # Represent float
        r = repr(obj)
        return r
    if isinstance(obj, str):
        return _encode_string(obj)
    if isinstance(obj, (list, tuple)):
        if not obj:
            return '[]'
        if indent is not None:
            next_indent = _current_indent + indent
            indent_str = '\n' + ' ' * next_indent
            close_str = '\n' + ' ' * _current_indent
            items = [indent_str + _encode_value(
                v, sort_keys=sort_keys, indent=indent,
                _current_indent=next_indent,
                separators=separators, default=default)
                for v in obj]
            return '[' + item_sep.join(items) + close_str + ']'
        else:
            items = [_encode_value(v, sort_keys=sort_keys, indent=indent,
                                   _current_indent=_current_indent,
                                   separators=separators, default=default)
                     for v in obj]
            return '[' + item_sep.join(items) + ']'
    if isinstance(obj, dict):
        if not obj:
            return '{}'
        keys = sorted(obj.keys()) if sort_keys else list(obj.keys())
        if indent is not None:
            next_indent = _current_indent + indent
            indent_str = '\n' + ' ' * next_indent
            close_str = '\n' + ' ' * _current_indent
            pairs = [
                indent_str + _encode_string(str(k)) + key_sep +
                _encode_value(obj[k], sort_keys=sort_keys, indent=indent,
                              _current_indent=next_indent,
                              separators=separators, default=default)
                for k in keys
            ]
            return '{' + item_sep.join(pairs) + close_str + '}'
        else:
            pairs = [
                _encode_string(str(k)) + key_sep +
                _encode_value(obj[k], sort_keys=sort_keys, indent=indent,
                              _current_indent=_current_indent,
                              separators=separators, default=default)
                for k in keys
            ]
            return '{' + item_sep.join(pairs) + '}'
    # Try default
    if default is not None:
        return _encode_value(default(obj), sort_keys=sort_keys, indent=indent,
                             _current_indent=_current_indent,
                             separators=separators, default=default)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=False, cls=None, indent=None, separators=None,
          default=None, sort_keys=False, **kw):
    """Serialize obj to a JSON-formatted string."""
    return _encode_value(obj, sort_keys=sort_keys, indent=indent,
                         separators=separators, default=default)


def dump(obj, fp, **kw):
    """Serialize obj to a JSON-formatted stream to fp."""
    fp.write(dumps(obj, **kw))


# ---------------------------------------------------------------------------
# JSONEncoder / JSONDecoder classes
# ---------------------------------------------------------------------------

class JSONEncoder:
    def __init__(self, *, skipkeys=False, ensure_ascii=True,
                 check_circular=True, allow_nan=False, sort_keys=False,
                 indent=None, separators=None, default=None):
        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        self.separators = separators
        self.default_func = default

    def default(self, obj):
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def encode(self, obj):
        return dumps(obj, sort_keys=self.sort_keys, indent=self.indent,
                     separators=self.separators,
                     default=self.default_func or self.default)

    def iterencode(self, obj):
        yield self.encode(obj)


class JSONDecoder:
    def __init__(self, *, object_hook=None, parse_float=None,
                 parse_int=None, parse_constant=None,
                 strict=True, object_pairs_hook=None):
        self.object_hook = object_hook
        self.parse_float = parse_float
        self.parse_int = parse_int
        self.parse_constant = parse_constant
        self.strict = strict
        self.object_pairs_hook = object_pairs_hook

    def decode(self, s):
        return loads(s, object_hook=self.object_hook)

    def raw_decode(self, s, idx=0):
        end = len(s)
        value, new_idx = _parse_value(s, idx, end)
        return value, new_idx


# ---------------------------------------------------------------------------
# Zero-arg invariant helpers
# ---------------------------------------------------------------------------

def json5_decode_error() -> bool:
    """Return True if loads('invalid json') raises JSONDecodeError."""
    try:
        loads('invalid json')
        return False
    except JSONDecodeError:
        return True


def json5_sort_keys() -> str:
    """Return dumps({'b': 2, 'a': 1}, sort_keys=True)."""
    return dumps({'b': 2, 'a': 1}, sort_keys=True)


def json5_nested():
    """Return loads('{"a":{"b":[1,2,3]}}')['a']['b']."""
    return loads('{"a":{"b":[1,2,3]}}')['a']['b']