# generation A literal scan


def literal_eval(text):
    if not isinstance(text, str):
        raise TypeError(
            "literal_eval() arg 1 must be a string, not {}".format(type(text).__name__)
        )
    s = text
    n = len(s)
    pos = [0]

    def skip_ws():
        i = pos[0]
        while i < n:
            c = s[i]
            if c in " \t\n\r\f\v":
                i += 1
                continue
            if c == "#":
                while i < n and s[i] != "\n":
                    i += 1
                continue
            break
        pos[0] = i

    def peek():
        skip_ws()
        if pos[0] >= n:
            return ""
        return s[pos[0]]

    def expect(ch):
        skip_ws()
        if pos[0] >= n or s[pos[0]] != ch:
            raise SyntaxError("invalid syntax")
        pos[0] += 1

    def is_hex(c):
        return c.isdigit() or c.lower() in "abcdef"

    def strip_underscores(token):
        if not token:
            raise SyntaxError("invalid syntax")
        if token[0] == "_" or token[-1] == "_":
            raise SyntaxError("invalid syntax")
        parts = token.split("_")
        for p in parts:
            if not p:
                raise SyntaxError("invalid syntax")
        return token.replace("_", "")

    def parse():
        skip_ws()
        if pos[0] >= n:
            raise ValueError("malformed node or string")
        val = parse_expr()
        skip_ws()
        if pos[0] != n:
            raise SyntaxError("invalid syntax")
        return val

    def parse_expr():
        if pos[0] < n and s[pos[0]] in "+-":
            sign = -1 if s[pos[0]] == "-" else 1
            pos[0] += 1
            skip_ws()
            if pos[0] < n and (s[pos[0]].isdigit() or s[pos[0]] == "."):
                return parse_complex_tail(sign)
            raise SyntaxError("invalid syntax")
        c = peek()
        if c.isdigit() or c == ".":
            return parse_complex_tail(1)
        return parse_atom()

    def parse_complex_tail(unary_sign):
        real = parse_number()
        if isinstance(real, bool):
            raise SyntaxError("invalid syntax")
        skip_ws()
        if pos[0] < n and s[pos[0]] in "jJ":
            pos[0] += 1
            imag = float(real) if isinstance(real, float) else real
            return complex(0, unary_sign * imag)
        if pos[0] < n and s[pos[0]] in "+-":
            op = s[pos[0]]
            pos[0] += 1
            imag_part = parse_number()
            skip_ws()
            if pos[0] >= n or s[pos[0]] not in "jJ":
                raise ValueError("malformed node or string")
            pos[0] += 1
            if isinstance(imag_part, bool):
                raise SyntaxError("invalid syntax")
            imag = float(imag_part) if isinstance(imag_part, float) else imag_part
            if op == "+":
                return complex(unary_sign * real, imag)
            return complex(unary_sign * real, -imag)
        if unary_sign < 0:
            if isinstance(real, float):
                return -real
            return -real
        return real

    def parse_number():
        skip_ws()
        if pos[0] >= n:
            raise SyntaxError("invalid syntax")
        i = pos[0]
        start = i

        if s[i:i + 2].lower() == "0x":
            i += 2
            if i >= n or not is_hex(s[i]):
                raise SyntaxError("invalid syntax")
            while i < n and (is_hex(s[i]) or s[i] == "_"):
                i += 1
            val = int(strip_underscores(s[start + 2:i]), 16)
            pos[0] = i
            return val

        if s[i:i + 2].lower() == "0o":
            i += 2
            if i >= n:
                raise SyntaxError("invalid syntax")
            while i < n and s[i] in "01234567_":
                if s[i] in "89":
                    raise SyntaxError("invalid syntax")
                i += 1
            val = int(strip_underscores(s[start + 2:i]), 8)
            pos[0] = i
            return val

        if s[i:i + 2].lower() == "0b":
            i += 2
            if i >= n:
                raise SyntaxError("invalid syntax")
            while i < n and s[i] in "01_":
                i += 1
            val = int(strip_underscores(s[start + 2:i]), 2)
            pos[0] = i
            return val

        if s[i] == "0" and i + 1 < n and s[i + 1].isdigit():
            raise SyntaxError("invalid syntax")

        saw_dot = False
        saw_exp = False
        while i < n:
            c = s[i]
            if c == "_":
                i += 1
                continue
            if c == ".":
                if saw_dot or saw_exp:
                    break
                saw_dot = True
                i += 1
                continue
            if c in "eE":
                if saw_exp:
                    break
                saw_exp = True
                i += 1
                if i < n and s[i] in "+-":
                    i += 1
                continue
            if c.isdigit():
                i += 1
                continue
            break

        token = s[start:i]
        if not token:
            raise SyntaxError("invalid syntax")
        pos[0] = i
        if saw_dot or saw_exp:
            return float(strip_underscores(token))
        if token.endswith("."):
            return float(strip_underscores(token[:-1] + "."))
        return int(strip_underscores(token), 10)

    def parse_atom():
        skip_ws()
        if pos[0] >= n:
            raise SyntaxError("invalid syntax")
        c = s[pos[0]]

        if c in "'\"":
            return parse_string(c, raw=False, as_bytes=False)

        if c.isalpha() or c == "_":
            return parse_prefixed_or_name()

        if c == "[":
            return parse_list()
        if c == "{":
            return parse_dict_or_set()
        if c == "(":
            return parse_paren()

        if c.isdigit() or c == ".":
            return parse_complex_tail(1)

        raise SyntaxError("invalid syntax")

    def parse_prefixed_or_name():
        i = pos[0]
        start = i
        while i < n and (s[i].isalnum() or s[i] == "_"):
            i += 1
        name = s[start:i]
        pos[0] = i
        if name == "True":
            return True
        if name == "False":
            return False
        if name == "None":
            return None
        lower = name.lower()
        if lower in ("true", "false", "none"):
            raise SyntaxError("invalid syntax")
        if lower.startswith("f"):
            raise ValueError("malformed node or string")
        if lower == "u" or (lower.startswith("u") and lower != "u"):
            raise SyntaxError("invalid syntax")
        if name == "set":
            return parse_empty_call(set)
        if name == "frozenset":
            raise ValueError("malformed node or string")
        if lower[0] == "b" or lower in ("br", "rb"):
            skip_ws()
            if pos[0] >= n or s[pos[0]] not in "'\"":
                raise SyntaxError("invalid syntax")
            raw = "r" in lower
            return parse_string(s[pos[0]], raw=raw, as_bytes=True)
        if lower in ("r", "br", "rb"):
            skip_ws()
            if pos[0] >= n or s[pos[0]] not in "'\"":
                raise SyntaxError("invalid syntax")
            return parse_string(s[pos[0]], raw=True, as_bytes=False)
        raise SyntaxError("invalid syntax")

    def parse_empty_call(factory):
        skip_ws()
        if pos[0] >= n or s[pos[0]] != "(":
            raise SyntaxError("invalid syntax")
        pos[0] += 1
        skip_ws()
        if pos[0] >= n or s[pos[0]] != ")":
            raise ValueError("malformed node or string")
        pos[0] += 1
        return factory()

    def parse_string(quote, raw=False, as_bytes=False):
        if pos[0] >= n or s[pos[0]] != quote:
            raise SyntaxError("invalid syntax")
        if pos[0] + 2 < n and s[pos[0] + 1] == quote and s[pos[0] + 2] == quote:
            return read_triple(quote, raw, as_bytes)
        return read_single(quote, raw, as_bytes)

    def read_single(quote, raw, as_bytes):
        i = pos[0] + 1
        chunks = []
        while i < n:
            c = s[i]
            if c == "\\" and not raw:
                i, piece = decode_escape(i, as_bytes)
                chunks.append(piece)
                continue
            if c == quote:
                pos[0] = i + 1
                if as_bytes:
                    return b"".join(chunks)
                return "".join(chunks)
            if as_bytes:
                chunks.append(c.encode("latin-1"))
            else:
                chunks.append(c)
            i += 1
        raise SyntaxError("invalid syntax")

    def read_triple(quote, raw, as_bytes):
        i = pos[0] + 3
        chunks = []
        while i < n:
            if s[i:i + 3] == quote * 3:
                pos[0] = i + 3
                if as_bytes:
                    return b"".join(chunks)
                return "".join(chunks)
            c = s[i]
            if c == "\\" and not raw:
                i, piece = decode_escape(i, as_bytes)
                chunks.append(piece)
                continue
            if as_bytes:
                chunks.append(c.encode("latin-1"))
            else:
                chunks.append(c)
            i += 1
        raise SyntaxError("invalid syntax")

    def decode_escape(i, as_bytes):
        i += 1
        if i >= n:
            raise SyntaxError("invalid syntax")
        c = s[i]
        if c == "\n":
            return i + 1, (b"" if as_bytes else "")
        mapping = {
            "\\": 92,
            "'": 39,
            '"': 34,
            "a": 7,
            "b": 8,
            "f": 12,
            "n": 10,
            "r": 13,
            "t": 9,
            "v": 11,
        }
        if c in mapping:
            code = mapping[c]
            if as_bytes:
                return i + 1, bytes([code])
            return i + 1, chr(code)
        if c == "x":
            if i + 2 >= n:
                raise SyntaxError("invalid syntax")
            hx = s[i + 1:i + 3]
            try:
                byte = int(hx, 16)
            except ValueError:
                raise SyntaxError("invalid syntax")
            if as_bytes:
                return i + 3, bytes([byte])
            return i + 3, chr(byte)
        if c in "01234567":
            j = i
            while j < n and j < i + 3 and s[j] in "01234567":
                j += 1
            val = int(s[i:j], 8)
            if val > 255:
                raise SyntaxError("invalid syntax")
            if as_bytes:
                return j, bytes([val])
            return j, chr(val)
        if c == "u":
            if i + 4 >= n:
                raise SyntaxError("invalid syntax")
            hx = s[i + 1:i + 5]
            try:
                code = int(hx, 16)
            except ValueError:
                raise SyntaxError("invalid syntax")
            return i + 5, chr(code)
        if c == "U":
            if i + 8 >= n:
                raise SyntaxError("invalid syntax")
            hx = s[i + 1:i + 9]
            try:
                code = int(hx, 16)
            except ValueError:
                raise SyntaxError("invalid syntax")
            return i + 9, chr(code)
        if c == "N":
            raise SyntaxError("invalid syntax")
        if as_bytes:
            return i + 1, c.encode("latin-1")
        return i + 1, c

    def parse_list():
        expect("[")
        skip_ws()
        if peek() == "]":
            pos[0] += 1
            return []
        items = []
        while True:
            items.append(parse_expr())
            skip_ws()
            if peek() == "]":
                pos[0] += 1
                return items
            expect(",")
            skip_ws()
            if peek() == "]":
                pos[0] += 1
                return items

    def parse_paren():
        expect("(")
        skip_ws()
        if peek() == ")":
            pos[0] += 1
            return ()
        first = parse_expr()
        skip_ws()
        if peek() == ")":
            pos[0] += 1
            return first
        expect(",")
        items = [first]
        while True:
            skip_ws()
            if peek() == ")":
                pos[0] += 1
                return tuple(items)
            items.append(parse_expr())
            skip_ws()
            if peek() == ")":
                pos[0] += 1
                return tuple(items)
            expect(",")

    def parse_dict_or_set():
        expect("{")
        skip_ws()
        if peek() == "}":
            pos[0] += 1
            return {}
        is_dict = None
        result_dict = {}
        result_set = set()
        while True:
            key = parse_expr()
            skip_ws()
            if peek() == ":":
                if is_dict is False:
                    raise SyntaxError("invalid syntax")
                is_dict = True
                pos[0] += 1
                val = parse_expr()
                require_hashable(key)
                result_dict[key] = val
            else:
                if is_dict is True:
                    raise SyntaxError("invalid syntax")
                is_dict = False
                require_hashable(key)
                result_set.add(key)
            skip_ws()
            if peek() == "}":
                pos[0] += 1
                if is_dict:
                    return result_dict
                return result_set
            expect(",")
            skip_ws()
            if peek() == "}":
                pos[0] += 1
                if is_dict:
                    return result_dict
                return result_set

    def require_hashable(key):
        if isinstance(key, (list, dict, set)):
            raise TypeError("unhashable type: {}".format(type(key).__name__))
        try:
            hash(key)
        except TypeError:
            raise

    return parse()
