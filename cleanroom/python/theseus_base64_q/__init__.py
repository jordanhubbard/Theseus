"""
theseus_base64_q — Clean-room Base64/32/16 codecs (RFC 4648).
Do NOT import base64 or binascii.
"""

_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


class Error(ValueError):
    """Raised on invalid Base64/32/16 input when validate=True."""


def _to_bytes(data):
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("ascii")
    return bytes(data)


def _encode(data, alphabet, pad=True):
    data = _to_bytes(data)
    bits = 0
    acc = 0
    out = []
    # 6-bit groups
    for byte in data:
        acc = (acc << 8) | byte
        bits += 8
        while bits >= 6:
            bits -= 6
            out.append(alphabet[(acc >> bits) & 0x3F])
            acc &= (1 << bits) - 1
    if bits:
        out.append(alphabet[(acc << (6 - bits)) & 0x3F])
    encoded = "".join(out)
    if pad:
        while len(encoded) % 4:
            encoded += "="
    return encoded.encode("ascii")


def _decode(data, alphabet, validate=False):
    if isinstance(data, bytes):
        text = data.decode("ascii")
    else:
        text = str(data)
    text = text.strip()
    table = {ch: i for i, ch in enumerate(alphabet)}
    table["="] = 0
    cleaned = []
    for ch in text:
        if ch in table:
            cleaned.append(ch)
        elif ch.isspace():
            continue
        elif validate:
            raise Error("Non-base64 digit found")
    if validate and len(cleaned) % 4 != 0:
        raise Error("Invalid base64-encoded string")
    while cleaned and cleaned[-1] == "=":
        cleaned.pop()
    acc = 0
    bits = 0
    out = bytearray()
    for ch in cleaned:
        acc = (acc << 6) | table[ch]
        bits += 6
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
            acc &= (1 << bits) - 1
    return bytes(out)


def b64encode(s, altchars=None):
    alphabet = _STD
    if altchars is not None:
        alt = _to_bytes(altchars)
        alphabet = _STD[:62] + chr(alt[0]) + chr(alt[1])
    return _encode(s, alphabet)


def b64decode(s, altchars=None, validate=False):
    alphabet = _STD
    if altchars is not None:
        alt = _to_bytes(altchars)
        alphabet = _STD[:62] + chr(alt[0]) + chr(alt[1])
    return _decode(s, alphabet, validate=validate)


def urlsafe_b64encode(s):
    return _encode(s, _URL)


def urlsafe_b64decode(s):
    return _decode(s, _URL)


def _b32encode(data):
    data = _to_bytes(data)
    acc = 0
    bits = 0
    out = []
    for byte in data:
        acc = (acc << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append(_B32[(acc >> bits) & 0x1F])
            acc &= (1 << bits) - 1
    if bits:
        out.append(_B32[(acc << (5 - bits)) & 0x1F])
    encoded = "".join(out)
    while len(encoded) % 8:
        encoded += "="
    return encoded.encode("ascii")


def b32encode(s):
    return _b32encode(s)


def b32decode(s, casefold=False, map01=None):
    if isinstance(s, bytes):
        text = s.decode("ascii")
    else:
        text = str(s)
    if casefold:
        text = text.upper()
    table = {ch: i for i, ch in enumerate(_B32)}
    table["="] = 0
    cleaned = [ch for ch in text if ch in table]
    while cleaned and cleaned[-1] == "=":
        cleaned.pop()
    acc = 0
    bits = 0
    out = bytearray()
    for ch in cleaned:
        acc = (acc << 5) | table[ch]
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
            acc &= (1 << bits) - 1
    return bytes(out)


def b16encode(s):
    return _to_bytes(s).hex().upper().encode("ascii")


def b16decode(s, casefold=False):
    if isinstance(s, bytes):
        text = s.decode("ascii")
    else:
        text = str(s)
    if casefold:
        text = text.upper()
    return bytes.fromhex(text)


__all__ = [
    "Error",
    "b64encode",
    "b64decode",
    "urlsafe_b64encode",
    "urlsafe_b64decode",
    "b32encode",
    "b32decode",
    "b16encode",
    "b16decode",
]
