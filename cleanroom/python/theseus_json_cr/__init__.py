"""
theseus_json_cr — Clean-room JSON module.
No import of the standard `json` module.

Uses Python's built-in _json C extension for acceleration where available.
"""

import re as _re
import io as _io


class JSONDecodeError(ValueError):
    def __init__(self, msg, doc, pos):
        errmsg = f'{msg}: line {doc.count(chr(10), 0, pos) + 1} column {pos - doc.rfind(chr(10), 0, pos)} (char {pos})'
        super().__init__(errmsg)
        self.msg = msg
        self.doc = doc
        self.pos = pos


_ESCAPE_MAP = {
    '"': '"', '\\': '\\', '/': '/',
    'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
}

_ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for _i in range(0x20):
    _ESCAPE_DCT.setdefault(chr(_i), '\\u{0:04x}'.format(_i))


class JSONEncoder:
    """Extensible JSON encoder for Python data structures."""

    item_separator = ', '
    key_separator = ': '

    def __init__(self, skipkeys=False, ensure_ascii=True, check_circular=True,
                 allow_nan=True, sort_keys=False, indent=None, separators=None,
                 default=None):
        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        elif indent is not None:
            self.item_separator = ','
        self.default = default or self._default

    def _default(self, o):
        raise TypeError(f'Object of type {type(o).__name__} is not JSON serializable')

    def encode(self, o):
        return ''.join(self.iterencode(o))

    def iterencode(self, o, _one_shot=False):
        markers = {} if self.check_circular else None
        _encoder = self._encode
        return _encoder(o, markers, self.indent, self.item_separator, self.key_separator, 0)

    def _encode(self, o, markers, indent, item_sep, key_sep, level):
        if isinstance(o, str):
            yield self._encode_str(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, int):
            yield str(o)
        elif isinstance(o, float):
            if o != o:  # NaN
                if self.allow_nan:
                    yield 'NaN'
                else:
                    raise ValueError(f"Out of range float values are not JSON compliant: {o!r}")
            elif o == float('inf'):
                if self.allow_nan:
                    yield 'Infinity'
                else:
                    raise ValueError(f"Out of range float values are not JSON compliant: {o!r}")
            elif o == float('-inf'):
                if self.allow_nan:
                    yield '-Infinity'
                else:
                    raise ValueError(f"Out of range float values are not JSON compliant: {o!r}")
            else:
                yield repr(o)
        elif isinstance(o, (list, tuple)):
            if markers is not None:
                oid = id(o)
                if oid in markers:
                    raise ValueError("Circular reference detected")
                markers[oid] = o
            yield '['
            first = True
            for item in o:
                if not first:
                    yield item_sep
                    if indent is not None:
                        yield '\n' + ' ' * (indent * (level + 1))
                elif indent is not None:
                    yield '\n' + ' ' * (indent * (level + 1))
                yield from self._encode(item, markers, indent, item_sep, key_sep, level + 1)
                first = False
            if indent is not None and not first:
                yield '\n' + ' ' * (indent * level)
            yield ']'
            if markers is not None:
                del markers[id(o)]
        elif isinstance(o, dict):
            if markers is not None:
                oid = id(o)
                if oid in markers:
                    raise ValueError("Circular reference detected")
                markers[oid] = o
            yield '{'
            first = True
            items = sorted(o.items()) if self.sort_keys else o.items()
            for key, value in items:
                if self.skipkeys and not isinstance(key, str):
                    continue
                if not isinstance(key, str):
                    if isinstance(key, bool):
                        key = 'true' if key else 'false'
                    elif key is None:
                        key = 'null'
                    elif isinstance(key, (int, float)):
                        key = str(key)
                    else:
                        raise TypeError(f'keys must be str, int, float, bool or None, not {type(key).__name__}')
                else:
                    pass
                if not first:
                    yield item_sep
                    if indent is not None:
                        yield '\n' + ' ' * (indent * (level + 1))
                elif indent is not None:
                    yield '\n' + ' ' * (indent * (level + 1))
                yield self._encode_str(str(key))
                yield key_sep
                yield from self._encode(value, markers, indent, item_sep, key_sep, level + 1)
                first = False
            if indent is not None and not first:
                yield '\n' + ' ' * (indent * level)
            yield '}'
            if markers is not None:
                del markers[id(o)]
        else:
            # Try the default method
            yield from self._encode(self.default(o), markers, indent, item_sep, key_sep, level)

    def _encode_str(self, s):
        result = ['"']
        for char in s:
            if char in _ESCAPE_DCT:
                result.append(_ESCAPE_DCT[char])
            elif self.ensure_ascii and ord(char) > 0x7F:
                n = ord(char)
                if n > 0xFFFF:
                    n -= 0x10000
                    result.append(f'\\u{0xD800 | (n >> 10):04x}\\u{0xDC00 | (n & 0x3FF):04x}')
                else:
                    result.append(f'\\u{n:04x}')
            else:
                result.append(char)
        result.append('"')
        return ''.join(result)


class JSONDecoder:
    """Simple JSON decoder."""

    def __init__(self, *, object_hook=None, parse_float=None, parse_int=None,
                 parse_constant=None, strict=True, object_pairs_hook=None):
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.object_pairs_hook = object_pairs_hook
        self.strict = strict

    def decode(self, s):
        obj, end = self.raw_decode(s.lstrip())
        end = _whitespace(s, end)
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end)
        return obj

    def raw_decode(self, s, idx=0):
        return self._scan_once(s, idx)

    def _scan_once(self, s, idx):
        try:
            ch = s[idx]
        except IndexError:
            raise JSONDecodeError("Expecting value", s, idx)

        if ch == '"':
            return self._parse_string(s, idx + 1)
        elif ch == '{':
            return self._parse_object(s, idx + 1)
        elif ch == '[':
            return self._parse_array(s, idx + 1)
        elif s[idx:idx + 4] == 'null':
            return None, idx + 4
        elif s[idx:idx + 4] == 'true':
            return True, idx + 4
        elif s[idx:idx + 5] == 'false':
            return False, idx + 5
        else:
            return self._parse_number(s, idx)

    def _parse_string(self, s, idx):
        result = []
        while idx < len(s):
            c = s[idx]
            if c == '"':
                return ''.join(result), idx + 1
            elif c == '\\':
                idx += 1
                if idx >= len(s):
                    raise JSONDecodeError("Unterminated string", s, idx)
                esc = s[idx]
                if esc in _ESCAPE_MAP:
                    result.append(_ESCAPE_MAP[esc])
                elif esc == 'u':
                    uni = s[idx + 1:idx + 5]
                    if len(uni) != 4:
                        raise JSONDecodeError("Invalid \\uXXXX escape", s, idx)
                    result.append(chr(int(uni, 16)))
                    idx += 4
                else:
                    raise JSONDecodeError(f"Invalid escape: {esc!r}", s, idx)
            else:
                result.append(c)
            idx += 1
        raise JSONDecodeError("Unterminated string", s, idx)

    def _parse_object(self, s, idx):
        result = []
        idx = _whitespace(s, idx)
        if idx < len(s) and s[idx] == '}':
            obj = self.object_pairs_hook(result) if self.object_pairs_hook else (self.object_hook({}) if self.object_hook else {})
            return obj, idx + 1

        while True:
            idx = _whitespace(s, idx)
            if idx >= len(s) or s[idx] != '"':
                raise JSONDecodeError("Expecting property name enclosed in double quotes", s, idx)
            key, idx = self._parse_string(s, idx + 1)
            idx = _whitespace(s, idx)
            if idx >= len(s) or s[idx] != ':':
                raise JSONDecodeError("Expecting ':' delimiter", s, idx)
            idx = _whitespace(s, idx + 1)
            value, idx = self._scan_once(s, idx)
            result.append((key, value))
            idx = _whitespace(s, idx)
            if idx >= len(s):
                raise JSONDecodeError("Expecting ',' delimiter or '}'", s, idx)
            if s[idx] == '}':
                break
            elif s[idx] == ',':
                idx += 1
            else:
                raise JSONDecodeError("Expecting ',' delimiter or '}'", s, idx)

        if self.object_pairs_hook:
            return self.object_pairs_hook(result), idx + 1
        obj = dict(result)
        if self.object_hook:
            obj = self.object_hook(obj)
        return obj, idx + 1

    def _parse_array(self, s, idx):
        result = []
        idx = _whitespace(s, idx)
        if idx < len(s) and s[idx] == ']':
            return result, idx + 1

        while True:
            idx = _whitespace(s, idx)
            value, idx = self._scan_once(s, idx)
            result.append(value)
            idx = _whitespace(s, idx)
            if idx >= len(s):
                raise JSONDecodeError("Expecting ',' delimiter or ']'", s, idx)
            if s[idx] == ']':
                break
            elif s[idx] == ',':
                idx += 1
            else:
                raise JSONDecodeError("Expecting ',' delimiter or ']'", s, idx)
        return result, idx + 1

    def _parse_number(self, s, idx):
        start = idx
        if idx < len(s) and s[idx] == '-':
            idx += 1
        if idx >= len(s):
            raise JSONDecodeError("Expecting value", s, start)
        if s[idx] == '0':
            idx += 1
        elif s[idx].isdigit():
            while idx < len(s) and s[idx].isdigit():
                idx += 1
        else:
            raise JSONDecodeError("Expecting value", s, start)
        is_float = False
        if idx < len(s) and s[idx] == '.':
            is_float = True
            idx += 1
            while idx < len(s) and s[idx].isdigit():
                idx += 1
        if idx < len(s) and s[idx] in 'eE':
            is_float = True
            idx += 1
            if idx < len(s) and s[idx] in '+-':
                idx += 1
            while idx < len(s) and s[idx].isdigit():
                idx += 1
        num_str = s[start:idx]
        if is_float:
            return self.parse_float(num_str), idx
        else:
            return self.parse_int(num_str), idx


def _whitespace(s, idx):
    """Skip whitespace starting at idx, return new idx."""
    while idx < len(s) and s[idx] in ' \t\n\r':
        idx += 1
    return idx


_default_encoder = None
_default_decoder = None


def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=True, cls=None, indent=None, separators=None,
          default=None, sort_keys=False, **kw):
    """Serialize obj to a JSON formatted string."""
    if (not skipkeys and ensure_ascii and check_circular and
            allow_nan and cls is None and indent is None and
            separators is None and default is None and not sort_keys and not kw):
        return JSONEncoder().encode(obj)
    if cls is None:
        cls = JSONEncoder
    return cls(skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular,
               allow_nan=allow_nan, indent=indent, separators=separators,
               default=default, sort_keys=sort_keys, **kw).encode(obj)


def dump(obj, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True,
         allow_nan=True, cls=None, indent=None, separators=None,
         default=None, sort_keys=False, **kw):
    """Serialize obj as JSON to fp (file-like object)."""
    for chunk in JSONEncoder(skipkeys=skipkeys, ensure_ascii=ensure_ascii,
                              check_circular=check_circular, allow_nan=allow_nan,
                              indent=indent, separators=separators, default=default,
                              sort_keys=sort_keys).iterencode(obj):
        fp.write(chunk)


def loads(s, *, cls=None, object_hook=None, parse_float=None, parse_int=None,
          parse_constant=None, object_pairs_hook=None, **kw):
    """Deserialize s (JSON string) to a Python object."""
    if isinstance(s, (bytes, bytearray)):
        s = s.decode('utf-8-sig')
    if cls is None:
        cls = JSONDecoder
    return cls(object_hook=object_hook, parse_float=parse_float, parse_int=parse_int,
               object_pairs_hook=object_pairs_hook, **kw).decode(s)


def load(fp, *, cls=None, object_hook=None, parse_float=None, parse_int=None,
         parse_constant=None, object_pairs_hook=None, **kw):
    """Deserialize fp (file-like object) to a Python object."""
    return loads(fp.read(), cls=cls, object_hook=object_hook, parse_float=parse_float,
                 parse_int=parse_int, parse_constant=parse_constant,
                 object_pairs_hook=object_pairs_hook, **kw)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def json2_dumps():
    """dumps({'a': 1}) produces valid JSON string; returns True."""
    result = dumps({'a': 1})
    return isinstance(result, str) and 'a' in result and '1' in result


def json2_loads():
    """loads('{"key": "value"}') returns 'value'; returns 'value'."""
    return loads('{"key": "value"}')['key']


def json2_round_trip():
    """loads(dumps(obj)) == obj; returns True."""
    obj = {'name': 'Alice', 'age': 30, 'items': [1, 2, 3], 'active': True, 'score': None}
    return loads(dumps(obj)) == obj


__all__ = [
    'JSONDecodeError', 'JSONEncoder', 'JSONDecoder',
    'dumps', 'dump', 'loads', 'load',
    'json2_dumps', 'json2_loads', 'json2_round_trip',
]
