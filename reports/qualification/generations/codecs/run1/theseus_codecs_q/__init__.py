# generation A rot13 scan

__all__ = ["encode"]


def _rot13_char(ch):
    o = ord(ch)
    if 65 <= o <= 90:
        return chr((o - 65 + 13) % 26 + 65)
    if 97 <= o <= 122:
        return chr((o - 97 + 13) % 26 + 97)
    return ch


def encode(text, encoding):
    if encoding == "rot_13":
        return "".join(_rot13_char(ch) for ch in text)
    raise LookupError("unknown encoding: %r" % (encoding,))
