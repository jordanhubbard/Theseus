# generation A uuid functions

import hashlib


def _normalize_hex(hex_string):
    if not isinstance(hex_string, str):
        raise TypeError("UUID hex argument must be a string")
    h = hex_string.replace("-", "").lower()
    if len(h) != 32:
        raise ValueError("badly formed hexadecimal UUID string")
    try:
        int(h, 16)
    except ValueError:
        raise ValueError("badly formed hexadecimal UUID string")
    return h


def _hex_to_hyphenated(h):
    return "%s-%s-%s-%s-%s" % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


class UUID(object):
    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None, int=None, version=None):
        if hex is not None and isinstance(hex, str) and bytes is None and bytes_le is None and fields is None and int is None:
            self._hex = _normalize_hex(hex)
            return
        if bytes is not None:
            if len(bytes) != 16:
                raise ValueError("bytes argument must be exactly 16 bytes long")
            self._hex = bytes.hex()
            return
        if hex is not None:
            self._hex = _normalize_hex(hex)
            return
        raise TypeError("one of the hex, bytes, bytes_le, fields, or int arguments must be given")

    @property
    def hex(self):
        return self._hex

    @property
    def bytes(self):
        return bytes.fromhex(self._hex)

    def __str__(self):
        return _hex_to_hyphenated(self._hex)

    def __repr__(self):
        return "UUID('%s')" % _hex_to_hyphenated(self._hex)


def uuid5(namespace, name):
    if isinstance(namespace, UUID):
        ns_bytes = namespace.bytes
    elif isinstance(namespace, str):
        ns_bytes = bytes.fromhex(_normalize_hex(namespace))
    else:
        raise TypeError("namespace must be UUID or str")
    if not isinstance(name, str):
        name = str(name)
    digest = hashlib.sha1(ns_bytes + name.encode("utf-8")).digest()
    b = bytearray(digest[:16])
    b[6] = (b[6] & 0x0F) | 0x50
    b[8] = (b[8] & 0x3F) | 0x80
    return _hex_to_hyphenated(bytes(b).hex())
