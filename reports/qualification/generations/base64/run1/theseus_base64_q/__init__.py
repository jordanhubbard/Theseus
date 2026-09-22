# generation A bitstring

"""Clean-room RFC 4648 base64/b32/b16 helpers (generation A bitstring)."""

_B64_STD = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B32_STD = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_WHITESPACE = b" \t\n\r\x0b\x0c"


def _to_bytes(data):
    if isinstance(data, str):
        try:
            return data.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("string argument should contain only ASCII characters") from exc
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    raise TypeError("expected bytes-like object or ASCII string")


def _bytes_to_bitstring(data):
    parts = []
    for byte in data:
        for shift in range(7, -1, -1):
            parts.append("1" if (byte >> shift) & 1 else "0")
    return "".join(parts)


def _bitstring_to_bytes(bits):
    if len(bits) % 8 != 0:
        raise ValueError("incorrect padding")
    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i : i + 8]
        value = 0
        for ch in chunk:
            value = (value << 1) | (1 if ch == "1" else 0)
        out.append(value)
    return bytes(out)


def _b64_sextet_value(ch, altchars, validate, urlsafe):
    if ch in _WHITESPACE:
        return None
    if ch == ord(b"="):
        return -1
    if ch == ord(b"+"):
        return 62
    if ch == ord(b"/"):
        return 63
    if urlsafe and ch == ord(b"-"):
        return 62
    if urlsafe and ch == ord(b"_"):
        return 63
    if altchars is not None:
        if ch == altchars[0]:
            return 62
        if ch == altchars[1]:
            return 63
    if ord(b"A") <= ch <= ord(b"Z"):
        return ch - ord(b"A")
    if ord(b"a") <= ch <= ord(b"z"):
        return ch - ord(b"a") + 26
    if ord(b"0") <= ch <= ord(b"9"):
        return ch - ord(b"0") + 52
    if validate:
        raise ValueError("Non-base64 digit found")
    return None


def _b64encode_bits(data, alphabet):
    bits = _bytes_to_bitstring(data)
    rem = len(bits) % 24
    if rem:
        bits = bits + ("0" * (24 - rem))
    out = bytearray()
    for i in range(0, len(bits), 6):
        idx = 0
        for ch in bits[i : i + 6]:
            idx = (idx << 1) | (1 if ch == "1" else 0)
        out.append(alphabet[idx])
    pad = (-len(data)) % 3
    if pad:
        out[-pad:] = b"=" * pad
    return bytes(out)


def _as_bytes(s):
    if isinstance(s, str):
        return _to_bytes(s)
    if isinstance(s, memoryview):
        return s.tobytes()
    return bytes(s)


def b64encode(s, altchars=None):
    if altchars is not None:
        if not isinstance(altchars, (bytes, bytearray)) or len(altchars) != 2:
            raise TypeError("altchars must be a 2-byte bytes-like object")
        altchars = bytes(altchars)
    data = _as_bytes(s)

    alphabet = bytearray(_B64_STD)
    if altchars is not None:
        alphabet[62] = altchars[0]
        alphabet[63] = altchars[1]
    return _b64encode_bits(data, alphabet)


def b64decode(s, altchars=None, validate=False):
    if altchars is not None:
        if not isinstance(altchars, (bytes, bytearray)) or len(altchars) != 2:
            raise TypeError("altchars must be a 2-byte bytes-like object")
        altchars = bytes(altchars)
    raw = _to_bytes(s)
    padlen = 0
    for ch in reversed(raw):
        if ch == ord(b"="):
            padlen += 1
        elif ch in _WHITESPACE:
            continue
        else:
            break
    if padlen > 2:
        raise ValueError("Incorrect padding")
    significant = 0
    for ch in raw:
        if ch in _WHITESPACE or ch == ord(b"="):
            continue
        significant += 1
    if (significant + padlen) % 4 != 0:
        raise ValueError("Incorrect padding")

    bits = []
    for ch in raw:
        if ch == ord(b"="):
            continue
        val = _b64_sextet_value(ch, altchars, validate, urlsafe=False)
        if val is None:
            continue
        if val < 0:
            continue
        for shift in range(5, -1, -1):
            bits.append("1" if (val >> shift) & 1 else "0")

    if padlen:
        discard = padlen * 2
        if len(bits) < discard:
            raise ValueError("Incorrect padding")
        bits = bits[: len(bits) - discard]

    return _bitstring_to_bytes("".join(bits))


def urlsafe_b64encode(s):
    return b64encode(s, altchars=b"-_")


def urlsafe_b64decode(s):
    raw = _to_bytes(s)
    padlen = 0
    for ch in reversed(raw):
        if ch == ord(b"="):
            padlen += 1
        elif ch in _WHITESPACE:
            continue
        else:
            break
    if padlen > 2:
        raise ValueError("Incorrect padding")
    significant = 0
    for ch in raw:
        if ch in _WHITESPACE or ch == ord(b"="):
            continue
        significant += 1
    if (significant + padlen) % 4 != 0:
        raise ValueError("Incorrect padding")

    bits = []
    for ch in raw:
        if ch == ord(b"="):
            continue
        val = _b64_sextet_value(ch, None, False, urlsafe=True)
        if val is None:
            continue
        for shift in range(5, -1, -1):
            bits.append("1" if (val >> shift) & 1 else "0")

    if padlen:
        discard = padlen * 2
        if len(bits) < discard:
            raise ValueError("Incorrect padding")
        bits = bits[: len(bits) - discard]

    return _bitstring_to_bytes("".join(bits))


def b32encode(s):
    data = bytes(s)
    bits = _bytes_to_bitstring(data)
    rem = len(bits) % 5
    if rem:
        bits = bits + ("0" * (5 - rem))
    out = bytearray()
    for i in range(0, len(bits), 5):
        idx = 0
        for ch in bits[i : i + 5]:
            idx = (idx << 1) | (1 if ch == "1" else 0)
        out.append(_B32_STD[idx])
    pad = (-len(out)) % 8
    if pad:
        out.extend(b"=" * pad)
    return bytes(out)


def b16encode(s):
    return bytes(s).hex().upper().encode("ascii")
