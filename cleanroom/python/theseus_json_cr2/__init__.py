"""
theseus_json_cr2 - Clean-room JSON implementation with extended utilities.
No import of json or any third-party library.
"""

import re
import math


# ---------------------------------------------------------------------------
# JSON Encoder
# ---------------------------------------------------------------------------

class JSONEncoder:
    """
    Extensible JSON encoder.

    Parameters
    ----------
    indent : int or str or None
        If not None, pretty-print with that indent level.
    sort_keys : bool
        If True, sort dict keys.
    separators : tuple (item_sep, key_sep) or None
    ensure_ascii : bool
        If True, escape non-ASCII characters.
    """

    def __init__(self, *, skipkeys=False, ensure_ascii=True,
                 check_circular=True, allow_nan=True,
                 sort_keys=False, indent=None, separators=None,
                 default=None):
        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        else:
            if indent is not None:
                self.item_separator = ','
                self.key_separator = ': '
            else:
                self.item_separator = ', '
                self.key_separator = ': '
        if default is not None:
            self.default = default

    def default(self, o):
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    def encode(self, o):
        return ''.join(self._encode_chunks(o, 0, set()))

    def iterencode(self, o):
        return self._encode_chunks(o, 0, set())

    def _encode_chunks(self, o, level, markers):
        if o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, int):
            yield self._encode_int(o)
        elif isinstance(o, float):
            yield self._encode_float(o)
        elif isinstance(o, str):
            yield self._encode_string(o)
        elif isinstance(o, (list, tuple)):
            yield from self._encode_list(o, level, markers)
        elif isinstance(o, dict):
            yield from self._encode_dict(o, level, markers)
        else:
            # Try default
            o2 = self.default(o)
            yield from self._encode_chunks(o2, level, markers)

    def _encode_int(self, o):
        return str(int(o))

    def _encode_float(self, o):
        if math.isnan(o):
            if self.allow_nan:
                return 'NaN'
            raise ValueError("Out of range float values are not JSON compliant")
        if math.isinf(o):
            if self.allow_nan:
                return 'Infinity' if o > 0 else '-Infinity'
            raise ValueError("Out of range float values are not JSON compliant")
        # Represent float
        r = repr(o)
        return r

    def _encode_string(self, s):
        chunks = ['"']
        for ch in s:
            if ch == '"':
                chunks.append('\\"')
            elif ch == '\\':
                chunks.append('\\\\')
            elif ch == '\n':
                chunks.append('\\n')
            elif ch == '\r':
                chunks.append('\\r')
            elif ch == '\t':
                chunks.append('\\t')
            elif ch == '\b':
                chunks.append('\\b')
            elif ch == '\f':
                chunks.append('\\f')
            elif ord(ch) < 0x20:
                chunks.append(f'\\u{ord(ch):04x}')
            elif self.ensure_ascii and ord(ch) > 127:
                cp = ord(ch)
                if cp > 0xFFFF:
                    # Encode as surrogate pair
                    cp -= 0x10000
                    high = 0xD800 + (cp >> 10)
                    low = 0xDC00 + (cp & 0x3FF)
                    chunks.append(f'\\u{high:04x}\\u{low:04x}')
                else:
                    chunks.append(f'\\u{cp:04x}')
            else:
                chunks.append(ch)
        chunks.append('"')
        return ''.join(chunks)

    def _encode_list(self, lst, level, markers):
        if self.check_circular:
            obj_id = id(lst)
            if obj_id in markers:
                raise ValueError("Circular reference detected")
            markers.add(obj_id)

        if not lst:
            if self.check_circular:
                markers.discard(id(lst))
            yield '[]'
            return

        yield '['
        indent = self.indent
        if indent is not None:
            if isinstance(indent, int):
                indent_str = ' ' * indent
            else:
                indent_str = str(indent)
            current_indent = indent_str * (level + 1)
            closing_indent = indent_str * level
            item_sep = self.item_separator + '\n' + current_indent
            yield '\n' + current_indent
        else:
            item_sep = self.item_separator
            current_indent = None
            closing_indent = None

        first = True
        for item in lst:
            if not first:
                yield item_sep
            first = False
            yield from self._encode_chunks(item, level + 1, markers)

        if indent is not None:
            yield '\n' + closing_indent

        yield ']'

        if self.check_circular:
            markers.discard(id(lst))

    def _encode_dict(self, dct, level, markers):
        if self.check_circular:
            obj_id = id(dct)
            if obj_id in markers:
                raise ValueError("Circular reference detected")
            markers.add(obj_id)

        if not dct:
            if self.check_circular:
                markers.discard(id(dct))
            yield '{}'
            return

        yield '{'
        indent = self.indent
        if indent is not None:
            if isinstance(indent, int):
                indent_str = ' ' * indent
            else:
                indent_str = str(indent)
            current_indent = indent_str * (level + 1)
            closing_indent = indent_str * level
            item_sep = self.item_separator + '\n' + current_indent
            yield '\n' + current_indent
        else:
            item_sep = self.item_separator
            current_indent = None
            closing_indent = None

        keys = list(dct.keys())
        if self.sort_keys:
            keys = sorted(keys, key=lambda k: str(k))

        first = True
        for key in keys:
            if not isinstance(key, str):
                if self.skipkeys:
                    continue
                if isinstance(key, (int, float, bool, type(None))):
                    key = _coerce_key(key)
                else:
                    raise TypeError(f"keys must be strings, not {type(key).__name__}")
            if not first:
                yield item_sep
            first = False
            yield self._encode_string(key)
            yield self.key_separator
            yield from self._encode_chunks(dct[key], level + 1, markers)

        if indent is not None:
            yield '\n' + closing_indent

        yield '}'

        if self.check_circular:
            markers.discard(id(dct))


def _coerce_key(key):
    if key is True:
        return 'true'
    if key is False:
        return 'false'
    if key is None:
        return 'null'
    return str(key)


# ---------------------------------------------------------------------------
# JSON Decoder
# ---------------------------------------------------------------------------

class JSONDecodeError(ValueError):
    def __init__(self, msg, doc, pos):
        lineno = doc.count('\n', 0, pos) + 1
        colno = pos - doc.rfind('\n', 0, pos)
        errmsg = f'{msg}: line {lineno} column {colno} (char {pos})'
        super().__init__(errmsg)
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = lineno
        self.colno = colno


class JSONDecoder:
    """
    Extensible JSON decoder.

    Parameters
    ----------
    object_hook : callable or None
        If provided, called with each decoded dict; return value replaces dict.
    parse_float : callable or None
        If provided, called with float string; default is float().
    parse_int : callable or None
        If provided, called with int string; default is int().
    parse_constant : callable or None
        Called for '-Infinity', 'Infinity', 'NaN'.
    object_pairs_hook : callable or None
        If provided, called with list of (key, value) pairs.
    """

    def __init__(self, *, object_hook=None, parse_float=None,
                 parse_int=None, parse_constant=None,
                 strict=True, object_pairs_hook=None):
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant
        self.strict = strict
        self.object_pairs_hook = object_pairs_hook

    def decode(self, s):
        obj, end = self.raw_decode(s)
        # Skip trailing whitespace
        end = _skip_whitespace(s, end)
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end)
        return obj

    def raw_decode(self, s, idx=0):
        idx = _skip_whitespace(s, idx)
        obj, idx = self._parse_value(s, idx)
        return obj, idx

    def _parse_value(self, s, idx):
        if idx >= len(s):
            raise JSONDecodeError("Expecting value", s, idx)
        ch = s[idx]
        if ch == '"':
            return self._parse_string(s, idx)
        elif ch == '{':
            return self._parse_object(s, idx)
        elif ch == '[':
            return self._parse_array(s, idx)
        elif ch == 'n':
            return self._parse_null(s, idx)
        elif ch == 't':
            return self._parse_true(s, idx)
        elif ch == 'f':
            return self._parse_false(s, idx)
        elif ch in '-0123456789':
            return self._parse_number(s, idx)
        elif ch == 'N' and s[idx:idx+3] == 'NaN':
            if self.parse_constant:
                return self.parse_constant('NaN'), idx + 3
            return float('nan'), idx + 3
        elif ch == 'I' and s[idx:idx+8] == 'Infinity':
            if self.parse_constant:
                return self.parse_constant('Infinity'), idx + 8
            return float('inf'), idx + 8
        else:
            raise JSONDecodeError("Expecting value", s, idx)

    def _parse_null(self, s, idx):
        if s[idx:idx+4] == 'null':
            return None, idx + 4
        raise JSONDecodeError("Expecting value", s, idx)

    def _parse_true(self, s, idx):
        if s[idx:idx+4] == 'true':
            return True, idx + 4
        raise JSONDecodeError("Expecting value", s, idx)

    def _parse_false(self, s, idx):
        if s[idx:idx+5] == 'false':
            return False, idx + 5
        raise JSONDecodeError("Expecting value", s, idx)

    def _parse_number(self, s, idx):
        # Match JSON number
        m = _NUMBER_RE.match(s, idx)
        if m is None:
            raise JSONDecodeError("Expecting value", s, idx)
        integer, frac, exp = m.group('int'), m.group('frac'), m.group('exp')
        if frac is None and exp is None:
            res = self.parse_int(integer)
        else:
            res = self.parse_float(m.group(0))
        return res, m.end()

    def _parse_string(self, s, idx):
        # idx points to opening "
        result, idx = _parse_string_at(s, idx, self.strict)
        return result, idx

    def _parse_object(self, s, idx):
        # idx points to '{'
        idx += 1  # skip '{'
        idx = _skip_whitespace(s, idx)
        pairs = []

        if idx < len(s) and s[idx] == '}':
            # Empty object
            obj = {}
            if self.object_pairs_hook is not None:
                obj = self.object_pairs_hook(pairs)
            elif self.object_hook is not None:
                obj = self.object_hook(obj)
            return obj, idx + 1

        while True:
            idx = _skip_whitespace(s, idx)
            if idx >= len(s) or s[idx] != '"':
                raise JSONDecodeError("Expecting property name enclosed in double quotes", s, idx)
            key, idx = _parse_string_at(s, idx, self.strict)
            idx = _skip_whitespace(s, idx)
            if idx >= len(s) or s[idx] != ':':
                raise JSONDecodeError("Expecting ':' delimiter", s, idx)
            idx += 1  # skip ':'
            idx = _skip_whitespace(s, idx)
            value, idx = self._parse_value(s, idx)
            pairs.append((key, value))
            idx = _skip_whitespace(s, idx)
            if idx >= len(s):
                raise JSONDecodeError("Expecting ',' delimiter or '}'", s, idx)
            ch = s[idx]
            if ch == '}':
                idx += 1
                break
            elif ch == ',':
                idx += 1
            else:
                raise JSONDecodeError("Expecting ',' delimiter or '}'", s, idx)

        if self.object_pairs_hook is not None:
            return self.object_pairs_hook(pairs), idx

        obj = dict(pairs)
        if self.object_hook is not None:
            obj = self.object_hook(obj)
        return obj, idx

    def _parse_array(self, s, idx):
        # idx points to '['
        idx += 1  # skip '['
        idx = _skip_whitespace(s, idx)
        values = []

        if idx < len(s) and s[idx] == ']':
            return values, idx + 1

        while True:
            idx = _skip_whitespace(s, idx)
            value, idx = self._parse_value(s, idx)
            values.append(value)
            idx = _skip_whitespace(s, idx)
            if idx >= len(s):
                raise JSONDecodeError("Expecting ',' delimiter or ']'", s, idx)
            ch = s[idx]
            if ch == ']':
                idx += 1
                break
            elif ch == ',':
                idx += 1
            else:
                raise JSONDecodeError("Expecting ',' delimiter or ']'", s, idx)

        return values, idx


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(
    r'(?P<int>-?(?:0|[1-9]\d*))'
    r'(?P<frac>\.\d+)?'
    r'(?P<exp>[eE][+-]?\d+)?'
)

_WHITESPACE_RE = re.compile(r'[ \t\n\r]*')

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


def _skip_whitespace(s, idx):
    m = _WHITESPACE_RE.match(s, idx)
    if m:
        return m.end()
    return idx


def _parse_string_at(s, idx, strict=True):
    """Parse a JSON string starting at idx (which must be '"')."""
    assert s[idx] == '"'
    idx += 1
    chunks = []
    begin = idx
    while True:
        if idx >= len(s):
            raise JSONDecodeError("Unterminated string starting at", s, begin - 1)
        ch = s[idx]
        if ch == '"':
            chunks.append(s[begin:idx])
            idx += 1
            return ''.join(chunks), idx
        elif ch == '\\':
            chunks.append(s[begin:idx])
            idx += 1
            if idx >= len(s):
                raise JSONDecodeError("Unterminated string starting at", s, begin - 1)
            esc = s[idx]
            if esc in _ESCAPE_MAP:
                chunks.append(_ESCAPE_MAP[esc])
                idx += 1
            elif esc == 'u':
                # Unicode escape
                uni_str = s[idx+1:idx+5]
                if len(uni_str) < 4:
                    raise JSONDecodeError("Invalid \\uXXXX escape", s, idx)
                try:
                    uni = int(uni_str, 16)
                except ValueError:
                    raise JSONDecodeError("Invalid \\uXXXX escape", s, idx)
                idx += 5
                # Handle surrogate pairs
                if 0xD800 <= uni <= 0xDBFF:
                    # High surrogate, expect low surrogate
                    if idx < len(s) - 1 and s[idx] == '\\' and s[idx+1] == 'u':
                        uni2_str = s[idx+2:idx+6]
                        if len(uni2_str) == 4:
                            try:
                                uni2 = int(uni2_str, 16)
                            except ValueError:
                                uni2 = 0
                            if 0xDC00 <= uni2 <= 0xDFFF:
                                uni = 0x10000 + (uni - 0xD800) * 0x400 + (uni2 - 0xDC00)
                                idx += 6
                chunks.append(chr(uni))
                begin = idx
                continue
            else:
                raise JSONDecodeError(f"Invalid \\escape: {esc!r}", s, idx)
            begin = idx
        elif strict and ord(ch) < 0x20:
            raise JSONDecodeError("Invalid control character at", s, idx)
        else:
            idx += 1


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
          allow_nan=True, cls=None, indent=None, separators=None,
          default=None, sort_keys=False, **kw):
    if cls is None:
        cls = JSONEncoder
    encoder = cls(
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw
    )
    return encoder.encode(obj)


def loads(s, *, cls=None, object_hook=None, parse_float=None,
          parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    if cls is None:
        cls = JSONDecoder
    decoder = cls(
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        **kw
    )
    return decoder.decode(s)


# ---------------------------------------------------------------------------
# Required exported test/demo functions
# ---------------------------------------------------------------------------

def json_cr2_object_hook():
    """
    Demonstrates object_hook: decodes a JSON object and converts the dict
    to a simple namespace-like object. Returns the value of key 'x' (42).
    """
    class _Obj:
        def __init__(self, d):
            self.__dict__.update(d)

    def hook(d):
        return _Obj(d)

    result = loads('{"x": 42, "y": "hello"}', object_hook=hook)
    return result.x


def json_cr2_indent():
    """
    Demonstrates indent: dumps({'a': 1}, indent=2) produces multi-line output.
    Returns True if the output contains a newline.
    """
    output = dumps({'a': 1}, indent=2)
    return '\n' in output


def json_cr2_sort_keys():
    """
    Demonstrates sort_keys: dumps({'b': 2, 'a': 1}, sort_keys=True)
    has 'a' before 'b'. Returns True if that is the case.
    """
    output = dumps({'b': 2, 'a': 1}, sort_keys=True)
    return output.index('"a"') < output.index('"b"')


__all__ = [
    'JSONEncoder',
    'JSONDecoder',
    'JSONDecodeError',
    'dumps',
    'loads',
    'json_cr2_object_hook',
    'json_cr2_indent',
    'json_cr2_sort_keys',
]