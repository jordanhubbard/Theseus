# generation A quopri scan

__all__ = ["encode", "decode", "encodestring", "decodestring"]

_HEX = b"0123456789ABCDEF"


def _as_bytes(s):
    if isinstance(s, bytes):
        return s
    if isinstance(s, bytearray):
        return bytes(s)
    if isinstance(s, memoryview):
        return s.tobytes()
    if isinstance(s, str):
        return s.encode("ascii")
    raise TypeError("argument must be bytes or ASCII string")


def _is_hex_byte(c):
    return (48 <= c <= 57) or (65 <= c <= 70) or (97 <= c <= 102)


def _quote_byte(c):
    return bytes((61, _HEX[c >> 4], _HEX[c & 0x0F]))


class _EncodedWriter(object):
    def __init__(self):
        self._out = bytearray()
        self._col = 0

    def _soft_break(self):
        self._out.extend(b"=\n")
        self._col = 0

    def write_quoted(self, c):
        if self._col > 73:
            self._soft_break()
        self._out.extend(_quote_byte(c))
        self._col += 3

    def write_literal(self, c):
        if self._col == 75:
            self._soft_break()
        self._out.append(c)
        self._col += 1

    def write(self, data):
        i = 0
        n = len(data)
        while i < n:
            c = data[i]
            if c == 13:
                self.write_literal(c)
                i += 1
                if i < n and data[i] == 10:
                    self.write_literal(10)
                    self._col = 0
                    i += 1
                continue
            if c == 10:
                self.write_literal(c)
                self._col = 0
                i += 1
                continue
            self.write_literal(c)
            i += 1

    def getvalue(self):
        return bytes(self._out)


def _trailing_start(line):
    trailing_start = len(line)
    while trailing_start > 0 and line[trailing_start - 1] in (32, 9):
        trailing_start -= 1
    return trailing_start


def _encode_line_body(line, quotetabs):
    if not line:
        return b""
    if quotetabs:
        out = bytearray()
        for c in line:
            if c == 61:
                out.extend(b"=3D")
            elif c == 32:
                out.extend(b"=20")
            elif c == 9:
                out.extend(b"=09")
            elif 32 <= c <= 126:
                out.append(c)
            else:
                out.extend(_quote_byte(c))
        return bytes(out)

    trailing_start = _trailing_start(line)
    has_trailing = trailing_start < len(line)
    out = bytearray()
    for idx, c in enumerate(line):
        if has_trailing and idx >= trailing_start and c in (32, 9):
            if idx == len(line) - 1:
                out.extend(_quote_byte(c))
            else:
                out.append(c)
            continue
        if c == 61:
            out.extend(b"=3D")
        elif c == 9:
            out.append(c)
        elif 32 <= c <= 126:
            out.append(c)
        else:
            out.extend(_quote_byte(c))
    return bytes(out)


def _encode_line_header(line, quotetabs):
    if not line:
        return b""
    if quotetabs:
        out = bytearray()
        for c in line:
            if c == 32:
                out.extend(b"=20")
            elif c == 9:
                out.extend(b"=09")
            elif c == 95:
                out.extend(b"=5F")
            elif c == 61:
                out.extend(b"=3D")
            elif 32 <= c <= 126:
                out.append(c)
            else:
                out.extend(_quote_byte(c))
        return bytes(out)

    trailing_start = _trailing_start(line)
    has_trailing = trailing_start < len(line)
    out = bytearray()
    for idx, c in enumerate(line):
        if has_trailing and idx >= trailing_start:
            if c == 32:
                out.append(95)
            elif c == 9:
                if idx == len(line) - 1:
                    out.extend(b"=09")
                else:
                    out.append(c)
            continue
        if c == 32:
            out.append(95)
        elif c == 95:
            out.extend(b"=5F")
        elif c == 61:
            out.extend(b"=3D")
        elif c == 9:
            out.append(c)
        elif 32 <= c <= 126:
            out.append(c)
        else:
            out.extend(_quote_byte(c))
    return bytes(out)


def _encode_line(line, quotetabs, header):
    if header:
        return _encode_line_header(line, quotetabs)
    return _encode_line_body(line, quotetabs)


def _encode_bytes(data, quotetabs=False, header=False):
    writer = _EncodedWriter()
    i = 0
    n = len(data)
    while i < n:
        j = i
        while j < n and data[j] not in (10, 13):
            j += 1
        writer.write(_encode_line(data[i:j], quotetabs, header))
        if j >= n:
            break
        if data[j] == 13:
            writer.write(b"\r")
            j += 1
            if j < n and data[j] == 10:
                writer.write(b"\n")
                j += 1
        else:
            writer.write(b"\n")
            j += 1
        i = j
    return writer.getvalue()


def _decode_bytes(data, header=False):
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        c = data[i]
        if c != 61:
            if header and c == 95:
                out.append(32)
            else:
                out.append(c)
            i += 1
            continue
        if i + 1 >= n:
            break
        n1 = data[i + 1]
        if n1 == 10:
            i += 2
            continue
        if n1 == 13:
            if i + 2 < n and data[i + 2] == 10:
                i += 3
            else:
                i += 2
            continue
        if i + 2 < n and _is_hex_byte(data[i + 1]) and _is_hex_byte(data[i + 2]):
            out.append(int(data[i + 1 : i + 3], 16))
            i += 3
            continue
        out.append(61)
        i += 1
        if i < n:
            out.append(data[i])
            i += 1
    return bytes(out)


def encodestring(s, quotetabs=False, header=False):
    return _encode_bytes(_as_bytes(s), quotetabs=quotetabs, header=header)


def decodestring(s, header=False):
    return _decode_bytes(_as_bytes(s), header=header)


def encode(input, output, quotetabs=False, header=False):
    data = input.read()
    if isinstance(data, str):
        data = data.encode("ascii")
    output.write(encodestring(data, quotetabs=quotetabs, header=header))


def decode(input, output, header=False):
    data = input.read()
    if isinstance(data, str):
        data = data.encode("ascii")
    output.write(decodestring(data, header=header))
