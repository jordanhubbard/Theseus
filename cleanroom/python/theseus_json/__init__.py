"""
theseus_json - Clean-room JSON codec implementation.
No imports of json, simplejson, or any JSON library.
"""

import math


class JSONDecodeError(ValueError):
    """Raised when loads() is given text that is not a single JSON value."""


__all__ = ["dumps", "loads", "JSONDecodeError"]


# ─────────────────────────────────────────────
#  ENCODER (dumps)
# ─────────────────────────────────────────────

def _u_escape(code):
    if code <= 0xFFFF:
        return "\\u{:04x}".format(code)
    code -= 0x10000
    hi = 0xD800 + (code >> 10)
    lo = 0xDC00 + (code & 0x3FF)
    return "\\u{:04x}\\u{:04x}".format(hi, lo)


def _encode_string(s, ensure_ascii=True):
    """Encode a Python string to a JSON string literal."""
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\b':
            out.append('\\b')
        elif ch == '\f':
            out.append('\\f')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif ord(ch) < 0x20:
            out.append(_u_escape(ord(ch)))
        elif ensure_ascii and ord(ch) > 0x7F:
            out.append(_u_escape(ord(ch)))
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _encode_value(obj, item_sep=", ", key_sep=": ", ensure_ascii=True):
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, int) and not isinstance(obj, bool):
        return str(obj)
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("JSON does not support NaN or Infinity")
        return repr(obj)
    if isinstance(obj, str):
        return _encode_string(obj, ensure_ascii=ensure_ascii)
    if isinstance(obj, (list, tuple)):
        items = [
            _encode_value(v, item_sep=item_sep, key_sep=key_sep, ensure_ascii=ensure_ascii)
            for v in obj
        ]
        return "[" + item_sep.join(items) + "]"
    if isinstance(obj, dict):
        pairs = []
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError("JSON object keys must be strings, got: {}".format(type(k)))
            pairs.append(
                _encode_string(k, ensure_ascii=ensure_ascii)
                + key_sep
                + _encode_value(v, item_sep=item_sep, key_sep=key_sep, ensure_ascii=ensure_ascii)
            )
        return "{" + item_sep.join(pairs) + "}"
    raise TypeError("Object of type {} is not JSON serializable".format(type(obj).__name__))


def dumps(obj, separators=None, ensure_ascii=True, **_kwargs):
    """Serialize obj to a JSON-formatted string."""
    item_sep, key_sep = ", ", ": "
    if separators is not None:
        item_sep, key_sep = separators
    return _encode_value(
        obj, item_sep=item_sep, key_sep=key_sep, ensure_ascii=ensure_ascii
    )


# ─────────────────────────────────────────────
#  DECODER (loads)
# ─────────────────────────────────────────────

class _Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def peek(self):
        self._skip_whitespace()
        if self.pos < len(self.text):
            return self.text[self.pos]
        return None

    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in ' \t\n\r':
            self.pos += 1

    def _expect(self, ch):
        self._skip_whitespace()
        if self.pos >= len(self.text) or self.text[self.pos] != ch:
            raise JSONDecodeError(
                "Expected '{}' at position {}, got '{}'".format(
                    ch, self.pos,
                    self.text[self.pos] if self.pos < len(self.text) else 'EOF'
                )
            )
        self.pos += 1

    def parse_value(self):
        self._skip_whitespace()
        if self.pos >= len(self.text):
            raise JSONDecodeError("Unexpected end of input")
        ch = self.text[self.pos]
        if ch == '"':
            return self.parse_string()
        elif ch == '{':
            return self.parse_object()
        elif ch == '[':
            return self.parse_array()
        elif ch == 't':
            return self.parse_literal('true', True)
        elif ch == 'f':
            return self.parse_literal('false', False)
        elif ch == 'n':
            return self.parse_literal('null', None)
        elif ch == '-' or ch.isdigit():
            return self.parse_number()
        else:
            raise JSONDecodeError("Unexpected character '{}' at position {}".format(ch, self.pos))

    def parse_literal(self, word, value):
        end = self.pos + len(word)
        if self.text[self.pos:end] == word:
            self.pos = end
            return value
        raise JSONDecodeError("Invalid literal at position {}".format(self.pos))

    def parse_string(self):
        self._expect('"')
        out = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '"':
                self.pos += 1
                return ''.join(out)
            elif ch == '\\':
                self.pos += 1
                if self.pos >= len(self.text):
                    raise JSONDecodeError("Unexpected end of string escape")
                esc = self.text[self.pos]
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
                    hex_str = self.text[self.pos:self.pos + 4]
                    if len(hex_str) < 4:
                        raise JSONDecodeError("Invalid unicode escape at position {}".format(self.pos))
                    code_point = int(hex_str, 16)
                    self.pos += 4
                    # Handle surrogate pairs
                    if 0xD800 <= code_point <= 0xDBFF:
                        # High surrogate, expect low surrogate
                        if self.text[self.pos:self.pos + 2] == '\\u':
                            self.pos += 2
                            hex_str2 = self.text[self.pos:self.pos + 4]
                            if len(hex_str2) < 4:
                                raise JSONDecodeError("Invalid surrogate pair at position {}".format(self.pos))
                            low = int(hex_str2, 16)
                            self.pos += 4
                            if 0xDC00 <= low <= 0xDFFF:
                                code_point = 0x10000 + (code_point - 0xD800) * 0x400 + (low - 0xDC00)
                                out.append(chr(code_point))
                            else:
                                raise JSONDecodeError("Invalid surrogate pair")
                        else:
                            raise JSONDecodeError("Missing low surrogate")
                    else:
                        out.append(chr(code_point))
                else:
                    raise JSONDecodeError("Invalid escape character '{}' at position {}".format(esc, self.pos))
            elif ord(ch) < 0x20:
                raise JSONDecodeError("Control character in string at position {}".format(self.pos))
            else:
                out.append(ch)
                self.pos += 1
        raise JSONDecodeError("Unterminated string")

    def parse_number(self):
        start = self.pos
        # Optional minus
        if self.pos < len(self.text) and self.text[self.pos] == '-':
            self.pos += 1
        # Integer part
        if self.pos < len(self.text) and self.text[self.pos] == '0':
            self.pos += 1
        elif self.pos < len(self.text) and self.text[self.pos].isdigit():
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        else:
            raise JSONDecodeError("Invalid number at position {}".format(self.pos))
        
        is_float = False
        # Fractional part
        if self.pos < len(self.text) and self.text[self.pos] == '.':
            is_float = True
            self.pos += 1
            if self.pos >= len(self.text) or not self.text[self.pos].isdigit():
                raise JSONDecodeError("Invalid number at position {}".format(self.pos))
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        
        # Exponent part
        if self.pos < len(self.text) and self.text[self.pos] in 'eE':
            is_float = True
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in '+-':
                self.pos += 1
            if self.pos >= len(self.text) or not self.text[self.pos].isdigit():
                raise JSONDecodeError("Invalid number at position {}".format(self.pos))
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        
        num_str = self.text[start:self.pos]
        if is_float:
            return float(num_str)
        else:
            return int(num_str)

    def parse_array(self):
        self._expect('[')
        self._skip_whitespace()
        result = []
        if self.pos < len(self.text) and self.text[self.pos] == ']':
            self.pos += 1
            return result
        while True:
            value = self.parse_value()
            result.append(value)
            self._skip_whitespace()
            if self.pos < len(self.text) and self.text[self.pos] == ',':
                self.pos += 1
            elif self.pos < len(self.text) and self.text[self.pos] == ']':
                self.pos += 1
                return result
            else:
                raise JSONDecodeError(
                    "Expected ',' or ']' at position {}, got '{}'".format(
                        self.pos,
                        self.text[self.pos] if self.pos < len(self.text) else 'EOF'
                    )
                )

    def parse_object(self):
        self._expect('{')
        self._skip_whitespace()
        result = {}
        if self.pos < len(self.text) and self.text[self.pos] == '}':
            self.pos += 1
            return result
        while True:
            self._skip_whitespace()
            key = self.parse_string()
            self._expect(':')
            value = self.parse_value()
            result[key] = value
            self._skip_whitespace()
            if self.pos < len(self.text) and self.text[self.pos] == ',':
                self.pos += 1
            elif self.pos < len(self.text) and self.text[self.pos] == '}':
                self.pos += 1
                return result
            else:
                raise JSONDecodeError(
                    "Expected ',' or '}}' at position {}, got '{}'".format(
                        self.pos,
                        self.text[self.pos] if self.pos < len(self.text) else 'EOF'
                    )
                )


def loads(s):
    """Deserialize s (a str) to a Python object."""
    if not isinstance(s, str):
        raise TypeError("loads() expects a str, got {}".format(type(s).__name__))
    parser = _Parser(s)
    value = parser.parse_value()
    parser._skip_whitespace()
    if parser.pos != len(parser.text):
        raise JSONDecodeError(
            "Extra data at position {}".format(parser.pos)
        )
    return value
