# generation A recursive descent

__all__ = ["dumps", "loads", "JSONDecodeError"]


class JSONDecodeError(ValueError):
    def __init__(self, msg, doc, pos):
        lineno = doc.count("\n", 0, pos) + 1
        colno = pos - doc.rfind("\n", 0, pos)
        errmsg = "%s: line %d column %d (char %d)" % (msg, lineno, colno, pos)
        ValueError.__init__(self, errmsg)
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = lineno
        self.colno = colno


_ESCAPE_DUMPS = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def _encode_string(s, ensure_ascii):
    parts = ['"']
    for ch in s:
        o = ord(ch)
        if ch in _ESCAPE_DUMPS:
            parts.append(_ESCAPE_DUMPS[ch])
        elif o < 0x20:
            parts.append("\\u%04x" % o)
        elif ensure_ascii and o > 0x7F:
            if o <= 0xFFFF:
                parts.append("\\u%04x" % o)
            else:
                o -= 0x10000
                high = 0xD800 + (o >> 10)
                low = 0xDC00 + (o & 0x3FF)
                parts.append("\\u%04x\\u%04x" % (high, low))
        else:
            parts.append(ch)
    parts.append('"')
    return "".join(parts)


def _encode_float(value):
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("Out of range float values are not JSON compliant")
    return repr(value)


def _encode(obj, ensure_ascii, item_separator, key_separator):
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, int) and not isinstance(obj, bool):
        return str(obj)
    if isinstance(obj, float):
        return _encode_float(obj)
    if isinstance(obj, str):
        return _encode_string(obj, ensure_ascii)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        items = [_encode(item, ensure_ascii, item_separator, key_separator) for item in obj]
        return "[" + item_separator.join(items) + "]"
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        pieces = []
        for key, val in obj.items():
            if not isinstance(key, str):
                raise TypeError("keys must be str, not %s" % type(key).__name__)
            encoded_key = _encode_string(key, ensure_ascii)
            encoded_val = _encode(val, ensure_ascii, item_separator, key_separator)
            pieces.append(encoded_key + key_separator + encoded_val)
        return "{" + item_separator.join(pieces) + "}"
    raise TypeError("Object of type %s is not JSON serializable" % type(obj).__name__)


def dumps(obj, separators=None, ensure_ascii=True):
    if separators is None:
        item_separator = ", "
        key_separator = ": "
    else:
        item_separator, key_separator = separators
    return _encode(obj, ensure_ascii, item_separator, key_separator)


_DOC = ""
_POS = 0


def _err(msg):
    raise JSONDecodeError(msg, _DOC, _POS)


def _peek():
    if _POS >= len(_DOC):
        return ""
    return _DOC[_POS]


def _advance(n=1):
    global _POS
    _POS += n


def _skip_ws():
    global _POS
    while _POS < len(_DOC) and _DOC[_POS] in " \t\n\r":
        _POS += 1


def _expect_literal(literal, msg):
    global _POS
    end = _POS + len(literal)
    if _DOC[_POS:end] != literal:
        _err(msg)
    _POS = end


def _decode_unicode_escape(hex_digits):
    return int(hex_digits, 16)


def parse_string():
    global _POS
    if _peek() != '"':
        _err('Expecting value')
    _advance(1)
    chars = []
    while _POS < len(_DOC):
        ch = _DOC[_POS]
        if ch == '"':
            _advance(1)
            return "".join(chars)
        if ch == "\\":
            _advance(1)
            if _POS >= len(_DOC):
                _err("Unterminated string starting at")
            esc = _DOC[_POS]
            _advance(1)
            if esc == '"':
                chars.append('"')
            elif esc == "\\":
                chars.append("\\")
            elif esc == "/":
                chars.append("/")
            elif esc == "b":
                chars.append("\b")
            elif esc == "f":
                chars.append("\f")
            elif esc == "n":
                chars.append("\n")
            elif esc == "r":
                chars.append("\r")
            elif esc == "t":
                chars.append("\t")
            elif esc == "u":
                if _POS + 4 > len(_DOC):
                    _err("Unterminated string starting at")
                hex_digits = _DOC[_POS : _POS + 4]
                if len(hex_digits) < 4 or any(c not in "0123456789abcdefABCDEF" for c in hex_digits):
                    _err("Invalid \\uXXXX escape")
                code = _decode_unicode_escape(hex_digits)
                _advance(4)
                if 0xD800 <= code <= 0xDBFF:
                    if _POS + 6 > len(_DOC) or _DOC[_POS : _POS + 2] != "\\u":
                        _err("Unterminated string starting at")
                    hex2 = _DOC[_POS + 2 : _POS + 6]
                    if len(hex2) < 4 or any(c not in "0123456789abcdefABCDEF" for c in hex2):
                        _err("Invalid \\uXXXX escape")
                    code2 = _decode_unicode_escape(hex2)
                    if not (0xDC00 <= code2 <= 0xDFFF):
                        _err("Invalid \\uXXXX escape")
                    _advance(6)
                    combined = 0x10000 + ((code - 0xD800) << 10) + (code2 - 0xDC00)
                    chars.append(chr(combined))
                elif 0xDC00 <= code <= 0xDFFF:
                    _err("Invalid \\uXXXX escape")
                else:
                    chars.append(chr(code))
            else:
                _err("Invalid \\escape")
            continue
        if ord(ch) < 0x20:
            _err("Invalid control character at")
        chars.append(ch)
        _advance(1)
    _err("Unterminated string starting at")


def parse_number():
    global _POS
    start = _POS
    if _peek() == "-":
        _advance(1)
    if _peek() == "0":
        _advance(1)
    elif _peek().isdigit():
        while _POS < len(_DOC) and _DOC[_POS].isdigit():
            _advance(1)
    else:
        _err("Expecting value")
    if _POS < len(_DOC) and _DOC[_POS] == ".":
        _advance(1)
        if _POS >= len(_DOC) or not _DOC[_POS].isdigit():
            _err("Expecting value")
        while _POS < len(_DOC) and _DOC[_POS].isdigit():
            _advance(1)
    if _POS < len(_DOC) and _DOC[_POS] in "eE":
        _advance(1)
        if _POS < len(_DOC) and _DOC[_POS] in "+-":
            _advance(1)
        if _POS >= len(_DOC) or not _DOC[_POS].isdigit():
            _err("Expecting value")
        while _POS < len(_DOC) and _DOC[_POS].isdigit():
            _advance(1)
    text = _DOC[start:_POS]
    if "." in text or "e" in text or "E" in text:
        return float(text)
    return int(text)


def parse_array():
    global _POS
    if _peek() != "[":
        _err("Expecting value")
    _advance(1)
    _skip_ws()
    if _peek() == "]":
        _advance(1)
        return []
    result = []
    while True:
        _skip_ws()
        result.append(parse_value())
        _skip_ws()
        if _peek() == "]":
            _advance(1)
            return result
        if _peek() != ",":
            _err("Expecting ',' delimiter")
        _advance(1)


def parse_object():
    global _POS
    if _peek() != "{":
        _err("Expecting value")
    _advance(1)
    _skip_ws()
    if _peek() == "}":
        _advance(1)
        return {}
    result = {}
    while True:
        _skip_ws()
        if _peek() != '"':
            _err("Expecting property name enclosed in double quotes")
        key = parse_string()
        _skip_ws()
        if _peek() != ":":
            _err("Expecting ':' delimiter")
        _advance(1)
        _skip_ws()
        result[key] = parse_value()
        _skip_ws()
        if _peek() == "}":
            _advance(1)
            return result
        if _peek() != ",":
            _err("Expecting ',' delimiter")
        _advance(1)


def parse_value():
    _skip_ws()
    if _POS >= len(_DOC):
        _err("Expecting value")
    ch = _peek()
    if ch == '"':
        return parse_string()
    if ch == "{":
        return parse_object()
    if ch == "[":
        return parse_array()
    if ch == "t":
        _expect_literal("true", "Expecting value")
        return True
    if ch == "f":
        _expect_literal("false", "Expecting value")
        return False
    if ch == "n":
        _expect_literal("null", "Expecting value")
        return None
    if ch == "-" or ch.isdigit():
        return parse_number()
    _err("Expecting value")


def loads(s):
    global _DOC, _POS
    if not isinstance(s, str):
        raise TypeError("the JSON object must be str, not %s" % type(s).__name__)
    _DOC = s
    _POS = 0
    if not s:
        raise JSONDecodeError("Expecting value", s, 0)
    _skip_ws()
    if _POS >= len(_DOC):
        raise JSONDecodeError("Expecting value", s, 0)
    value = parse_value()
    _skip_ws()
    if _POS != len(_DOC):
        raise JSONDecodeError("Extra data", s, _POS)
    return value
