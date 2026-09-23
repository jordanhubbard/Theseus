# generation A digest scan

__all__ = ["compare_digest"]


def compare_digest(a, b):
    if isinstance(a, str):
        if not isinstance(b, str):
            raise TypeError(
                "compare_digest() argument must be str or bytes-like"
            )
        if len(a) != len(b):
            return False
        acc = 0
        for ca, cb in zip(a, b):
            acc |= ord(ca) ^ ord(cb)
        return acc == 0
    if isinstance(a, (bytes, bytearray)):
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError(
                "compare_digest() argument must be str or bytes-like"
            )
        if len(a) != len(b):
            return False
        acc = 0
        for ca, cb in zip(a, b):
            acc |= ca ^ cb
        return acc == 0
    raise TypeError("compare_digest() argument must be str or bytes-like")
