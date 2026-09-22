# generation B decoder class


class JSONDecodeError(ValueError):
    def __init__(self, msg, doc, pos):
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = doc.count("\n", 0, pos) + 1
        line_start = doc.rfind("\n", 0, pos)
        self.colno = pos - line_start
        ValueError.__init__(
            self,
            "%s: line %d column %d (char %d)"
            % (msg, self.lineno, self.colno, pos),
        )


class Decoder:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def error(self, message, pos=None):
        if pos is None:
            pos = self.pos
        raise JSONDecodeError(message, self.text, pos)

    def skip_whitespace(self):
        while (
            self.pos < self.length
            and self.text[self.pos] in " \t\r\n"
        ):
            self.pos += 1

    def read_value(self):
        self.skip_whitespace()
        if self.pos >= self.length:
            self.error("Expecting value")

        char = self.text[self.pos]
        if char == '"':
            return self.read_string()
        if char == "{":
            return self.read_object()
        if char == "[":
            return self.read_array()
        if char == "t":
            return self.read_literal("true", True)
        if char == "f":
            return self.read_literal("false", False)
        if char == "n":
            return self.read_literal("null", None)
        if char == "-" or ("0" <= char <= "9"):
            return self.read_number()
        self.error("Expecting value")

    def read_literal(self, spelling, value):
        if self.text.startswith(spelling, self.pos):
            self.pos += len(spelling)
            return value
        self.error("Expecting value")

    def read_string(self):
        start = self.pos
        self.pos += 1
        pieces = []
        while self.pos < self.length:
            char = self.text[self.pos]
            self.pos += 1
            if char == '"':
                return "".join(pieces)
            if char == "\\":
                if self.pos >= self.length:
                    self.error("Unterminated string starting at", start)
                escape = self.text[self.pos]
                self.pos += 1
                simple = {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }
                if escape in simple:
                    pieces.append(simple[escape])
                elif escape == "u":
                    code = self.read_hex_escape()
                    if (
                        0xD800 <= code <= 0xDBFF
                        and self.text.startswith("\\u", self.pos)
                    ):
                        saved = self.pos
                        self.pos += 2
                        low = self.read_hex_escape()
                        if 0xDC00 <= low <= 0xDFFF:
                            code = (
                                0x10000
                                + ((code - 0xD800) << 10)
                                + (low - 0xDC00)
                            )
                        else:
                            self.pos = saved
                    pieces.append(chr(code))
                else:
                    self.error("Invalid \\escape", self.pos - 1)
            elif ord(char) < 0x20:
                self.error("Invalid control character at", self.pos - 1)
            else:
                pieces.append(char)
        self.error("Unterminated string starting at", start)

    def read_hex_escape(self):
        start = self.pos
        end = start + 4
        if end > self.length:
            self.error("Invalid \\uXXXX escape", start)
        digits = self.text[start:end]
        for char in digits:
            if not (
                "0" <= char <= "9"
                or "a" <= char <= "f"
                or "A" <= char <= "F"
            ):
                self.error("Invalid \\uXXXX escape", start)
        self.pos = end
        return int(digits, 16)

    def read_number(self):
        start = self.pos
        if self.text[self.pos] == "-":
            self.pos += 1
            if self.pos >= self.length:
                self.error("Expecting value", start)

        if self.pos < self.length and self.text[self.pos] == "0":
            self.pos += 1
        elif (
            self.pos < self.length
            and "1" <= self.text[self.pos] <= "9"
        ):
            self.pos += 1
            while (
                self.pos < self.length
                and "0" <= self.text[self.pos] <= "9"
            ):
                self.pos += 1
        else:
            self.error("Expecting value", start)

        is_float = False
        if self.pos < self.length and self.text[self.pos] == ".":
            is_float = True
            self.pos += 1
            fraction_start = self.pos
            while (
                self.pos < self.length
                and "0" <= self.text[self.pos] <= "9"
            ):
                self.pos += 1
            if self.pos == fraction_start:
                self.error("Expecting digit")

        if (
            self.pos < self.length
            and self.text[self.pos] in "eE"
        ):
            is_float = True
            self.pos += 1
            if (
                self.pos < self.length
                and self.text[self.pos] in "+-"
            ):
                self.pos += 1
            exponent_start = self.pos
            while (
                self.pos < self.length
                and "0" <= self.text[self.pos] <= "9"
            ):
                self.pos += 1
            if self.pos == exponent_start:
                self.error("Expecting digit")

        token = self.text[start:self.pos]
        if is_float:
            return float(token)
        return int(token)

    def read_object(self):
        result = {}
        self.pos += 1
        self.skip_whitespace()
        if self.pos < self.length and self.text[self.pos] == "}":
            self.pos += 1
            return result

        while True:
            if self.pos >= self.length or self.text[self.pos] != '"':
                self.error("Expecting property name enclosed in double quotes")
            key = self.read_string()
            self.skip_whitespace()
            if self.pos >= self.length or self.text[self.pos] != ":":
                self.error("Expecting ':' delimiter")
            self.pos += 1
            result[key] = self.read_value()
            self.skip_whitespace()
            if self.pos >= self.length:
                self.error("Expecting ',' delimiter")
            char = self.text[self.pos]
            self.pos += 1
            if char == "}":
                return result
            if char != ",":
                self.error("Expecting ',' delimiter", self.pos - 1)
            self.skip_whitespace()

    def read_array(self):
        result = []
        self.pos += 1
        self.skip_whitespace()
        if self.pos < self.length and self.text[self.pos] == "]":
            self.pos += 1
            return result

        while True:
            result.append(self.read_value())
            self.skip_whitespace()
            if self.pos >= self.length:
                self.error("Expecting ',' delimiter")
            char = self.text[self.pos]
            self.pos += 1
            if char == "]":
                return result
            if char != ",":
                self.error("Expecting ',' delimiter", self.pos - 1)

    def decode(self):
        value = self.read_value()
        self.skip_whitespace()
        if self.pos != self.length:
            self.error("Extra data")
        return value


class Encoder:
    def __init__(self, separators=None, ensure_ascii=True):
        if separators is None:
            self.item_separator = ", "
            self.key_separator = ": "
        else:
            try:
                self.item_separator, self.key_separator = separators
            except (TypeError, ValueError):
                raise TypeError("separators must be a pair of strings")
            if not isinstance(self.item_separator, str) or not isinstance(
                self.key_separator, str
            ):
                raise TypeError("separators must be a pair of strings")
        self.ensure_ascii = ensure_ascii

    def encode(self, value):
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, str):
            return self.encode_string(value)
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value != value or value == float("inf") or value == float("-inf"):
                raise ValueError("Out of range float values are not JSON compliant")
            return repr(value)
        if isinstance(value, list):
            return "[" + self.item_separator.join(
                self.encode(item) for item in value
            ) + "]"
        if isinstance(value, dict):
            members = []
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError("keys must be str")
                members.append(
                    self.encode_string(key)
                    + self.key_separator
                    + self.encode(item)
                )
            return "{" + self.item_separator.join(members) + "}"
        raise TypeError(
            "Object of type %s is not JSON serializable"
            % type(value).__name__
        )

    def encode_string(self, value):
        pieces = ['"']
        short_escapes = {
            '"': '\\"',
            "\\": "\\\\",
            "\b": "\\b",
            "\f": "\\f",
            "\n": "\\n",
            "\r": "\\r",
            "\t": "\\t",
        }
        for char in value:
            if char in short_escapes:
                pieces.append(short_escapes[char])
                continue
            code = ord(char)
            if code < 0x20:
                pieces.append("\\u%04x" % code)
            elif self.ensure_ascii and code > 0x7F:
                if code <= 0xFFFF:
                    pieces.append("\\u%04x" % code)
                else:
                    code -= 0x10000
                    high = 0xD800 + (code >> 10)
                    low = 0xDC00 + (code & 0x3FF)
                    pieces.append("\\u%04x\\u%04x" % (high, low))
            else:
                pieces.append(char)
        pieces.append('"')
        return "".join(pieces)


def dumps(obj, separators=None, ensure_ascii=True):
    return Encoder(separators, ensure_ascii).encode(obj)


def loads(s):
    if not isinstance(s, str):
        raise TypeError("the JSON object must be str")
    return Decoder(s).decode()


__all__ = ["dumps", "loads", "JSONDecodeError"]
