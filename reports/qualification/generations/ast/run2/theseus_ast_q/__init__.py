# generation B literal class
import re
import unicodedata


_DECIMAL_INTEGER = r"(?:0(?:_?0)*|[1-9](?:_?\d)*)"
_DIGITS = r"(?:\d(?:_?\d)*)"
_EXPONENT = r"(?:[eE][+-]?" + _DIGITS + r")"
_FLOAT = (
    r"(?:(?:"
    + _DIGITS
    + r"\.(?:"
    + _DIGITS
    + r")?|(?:"
    + _DIGITS
    + r")?\."
    + _DIGITS
    + r")(?:"
    + _EXPONENT
    + r")?|"
    + _DIGITS
    + _EXPONENT
    + r")"
)
_BASED_INTEGER = r"(?:0[xX][0-9a-fA-F](?:_?[0-9a-fA-F])*|0[oO][0-7](?:_?[0-7])*|0[bB][01](?:_?[01])*)"
_REAL_COMPONENT = r"(?:" + _FLOAT + r"|" + _BASED_INTEGER + r"|" + _DECIMAL_INTEGER + r")"
_IMAG_COMPONENT = r"(?:(?:" + _FLOAT + r"|" + _DIGITS + r")[jJ])"
_NUMBER_COMPONENT = re.compile(r"(?:" + _IMAG_COMPONENT + r"|" + _REAL_COMPONENT + r")")
_IMAG_ONLY = re.compile(r"(?:" + _IMAG_COMPONENT + r")\Z")
_FLOAT_ONLY = re.compile(r"(?:" + _FLOAT + r")\Z")
_BASED_ONLY = re.compile(r"(?:" + _BASED_INTEGER + r")\Z")


class _Literals:
    def __init__(self, text):
        if not isinstance(text, str):
            raise TypeError("literal_eval expects a string")
        self.text = text
        self.pos = 0
        self.length = len(text)

    def parse(self):
        self._space()
        value = self._value()
        self._space()
        if self.pos != self.length:
            self._error()
        return value

    def _error(self, message="malformed literal"):
        raise ValueError(message)

    def _space(self):
        while self.pos < self.length and self.text[self.pos] in " \t\r\n\f\v":
            self.pos += 1

    def _value(self):
        self._space()
        if self.pos >= self.length:
            self._error()
        char = self.text[self.pos]
        if char == "[":
            return self._list()
        if char == "(":
            return self._tuple_or_group()
        if char == "{":
            return self._dict_or_set()
        if char in "'\"" or self._string_starts_here():
            return self._strings()
        if self.text.startswith("True", self.pos):
            return self._word("True", True)
        if self.text.startswith("False", self.pos):
            return self._word("False", False)
        if self.text.startswith("None", self.pos):
            return self._word("None", None)
        if self.text.startswith("set", self.pos):
            return self._empty_set()
        if char in "+-." or char.isdigit():
            return self._number()
        self._error()

    def _word(self, word, value):
        end = self.pos + len(word)
        if end < self.length and (self.text[end].isalnum() or self.text[end] == "_"):
            self._error()
        self.pos = end
        return value

    def _empty_set(self):
        start = self.pos
        self.pos += 3
        self._space()
        if self.pos >= self.length or self.text[self.pos] != "(":
            self.pos = start
            self._error()
        self.pos += 1
        self._space()
        if self.pos >= self.length or self.text[self.pos] != ")":
            self.pos = start
            self._error()
        self.pos += 1
        return set()

    def _list(self):
        self.pos += 1
        values = []
        self._space()
        if self._take("]"):
            return values
        while True:
            values.append(self._value())
            self._space()
            if self._take("]"):
                return values
            self._expect(",")
            self._space()
            if self._take("]"):
                return values

    def _tuple_or_group(self):
        self.pos += 1
        self._space()
        if self._take(")"):
            return ()
        first = self._value()
        self._space()
        if self._take(")"):
            return first
        self._expect(",")
        values = [first]
        self._space()
        if self._take(")"):
            return tuple(values)
        while True:
            values.append(self._value())
            self._space()
            if self._take(")"):
                return tuple(values)
            self._expect(",")
            self._space()
            if self._take(")"):
                return tuple(values)

    def _dict_or_set(self):
        self.pos += 1
        self._space()
        if self._take("}"):
            return {}
        first = self._value()
        self._space()
        if self._take(":"):
            result = {}
            result[first] = self._value()
            self._space()
            while not self._take("}"):
                self._expect(",")
                self._space()
                if self._take("}"):
                    return result
                key = self._value()
                self._space()
                self._expect(":")
                result[key] = self._value()
                self._space()
            return result
        result = {first}
        while True:
            self._space()
            if self._take("}"):
                return result
            self._expect(",")
            self._space()
            if self._take("}"):
                return result
            result.add(self._value())

    def _take(self, token):
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def _expect(self, token):
        if not self._take(token):
            self._error("expected " + token)

    def _number(self):
        sign = ""
        if self.pos < self.length and self.text[self.pos] in "+-":
            sign = self.text[self.pos]
            self.pos += 1
            self._space()
        match = _NUMBER_COMPONENT.match(self.text, self.pos)
        if match is None:
            self._error("invalid number")
        token = sign + match.group(0)
        self.pos = match.end()
        first_is_imag = _IMAG_ONLY.fullmatch(match.group(0)) is not None
        if not first_is_imag:
            saved = self.pos
            self._space()
            if self.pos < self.length and self.text[self.pos] in "+-":
                operator = self.text[self.pos]
                self.pos += 1
                self._space()
                imaginary = _NUMBER_COMPONENT.match(self.text, self.pos)
                if imaginary is not None and _IMAG_ONLY.fullmatch(imaginary.group(0)) is not None:
                    token += operator + imaginary.group(0)
                    self.pos = imaginary.end()
                else:
                    self.pos = saved
            else:
                self.pos = saved
        return self._convert_number(token)

    def _convert_number(self, token):
        compact = token.replace("_", "")
        try:
            if compact[-1:] in "jJ":
                return complex(compact)
            unsigned = compact.lstrip("+-")
            if _FLOAT_ONLY.fullmatch(unsigned) is not None:
                return float(compact)
            if _BASED_ONLY.fullmatch(unsigned) is not None:
                sign = -1 if compact.startswith("-") else 1
                return sign * int(unsigned, 0)
            return int(compact, 10)
        except (ValueError, OverflowError):
            self._error("invalid number")

    def _string_starts_here(self):
        position = self.pos
        while position < self.length and position - self.pos < 2 and self.text[position] in "rRbBuU":
            position += 1
        return position < self.length and self.text[position] in "'\""

    def _strings(self):
        value = self._one_string()
        while True:
            saved = self.pos
            self._space()
            if not self._string_starts_here() and (
                self.pos >= self.length or self.text[self.pos] not in "'\""
            ):
                self.pos = saved
                return value
            following = self._one_string()
            if isinstance(value, bytes) != isinstance(following, bytes):
                self._error("cannot mix bytes and text literals")
            value += following

    def _one_string(self):
        prefix_start = self.pos
        while self.pos < self.length and self.pos - prefix_start < 2 and self.text[self.pos] in "rRbBuU":
            self.pos += 1
        prefix = self.text[prefix_start:self.pos].lower()
        if prefix not in ("", "r", "u", "b", "br", "rb"):
            self._error("invalid string prefix")
        if self.pos >= self.length or self.text[self.pos] not in "'\"":
            self._error("invalid string literal")
        quote = self.text[self.pos]
        triple = self.text.startswith(quote * 3, self.pos)
        delimiter = quote * (3 if triple else 1)
        self.pos += len(delimiter)
        raw = "r" in prefix
        binary = "b" in prefix
        pieces = []
        while self.pos < self.length:
            if self.text.startswith(delimiter, self.pos):
                self.pos += len(delimiter)
                if binary:
                    try:
                        return bytes(pieces)
                    except ValueError:
                        self._error("bytes literal out of range")
                return "".join(pieces)
            char = self.text[self.pos]
            if not triple and char in "\r\n":
                self._error("unterminated string literal")
            self.pos += 1
            if char == "\\" and raw:
                self._append_character(pieces, "\\", binary)
                if self.pos < self.length and self.text[self.pos] == quote:
                    self._append_character(pieces, quote, binary)
                    self.pos += 1
                continue
            if char != "\\":
                if binary:
                    code = ord(char)
                    if code > 127:
                        self._error("bytes can only contain ASCII characters")
                    pieces.append(code)
                else:
                    pieces.append(char)
                continue
            self._escape(pieces, binary)
        self._error("unterminated string literal")

    def _escape(self, pieces, binary):
        if self.pos >= self.length:
            self._error("unterminated escape")
        char = self.text[self.pos]
        self.pos += 1
        if char == "\n":
            return
        if char == "\r":
            if self.pos < self.length and self.text[self.pos] == "\n":
                self.pos += 1
            return
        simple = {
            "\\": "\\",
            "'": "'",
            '"': '"',
            "a": "\a",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "v": "\v",
        }
        if char in simple:
            self._append_character(pieces, simple[char], binary)
            return
        if char in "01234567":
            digits = char
            while len(digits) < 3 and self.pos < self.length and self.text[self.pos] in "01234567":
                digits += self.text[self.pos]
                self.pos += 1
            value = int(digits, 8)
            if binary:
                pieces.append(value & 255)
            else:
                pieces.append(chr(value))
            return
        if char == "x":
            self._hex_escape(pieces, 2, binary)
            return
        if char in "uU" and not binary:
            self._hex_escape(pieces, 4 if char == "u" else 8, False)
            return
        if char == "N" and not binary:
            if self.pos >= self.length or self.text[self.pos] != "{":
                self._error("invalid named escape")
            end = self.text.find("}", self.pos + 1)
            if end < 0:
                self._error("invalid named escape")
            name = self.text[self.pos + 1:end]
            self.pos = end + 1
            try:
                pieces.append(unicodedata.lookup(name))
            except KeyError:
                self._error("unknown Unicode character name")
            return
        self._append_character(pieces, "\\" + char, binary)

    def _hex_escape(self, pieces, count, binary):
        end = self.pos + count
        digits = self.text[self.pos:end]
        if len(digits) != count or any(char not in "0123456789abcdefABCDEF" for char in digits):
            self._error("invalid hexadecimal escape")
        self.pos = end
        value = int(digits, 16)
        if value > 0x10FFFF:
            self._error("Unicode escape out of range")
        if binary:
            pieces.append(value)
        else:
            pieces.append(chr(value))

    def _append_character(self, pieces, value, binary):
        if binary:
            for char in value:
                code = ord(char)
                if code > 255:
                    self._error("bytes literal out of range")
                pieces.append(code)
        else:
            pieces.append(value)


def literal_eval(text):
    return _Literals(text).parse()
