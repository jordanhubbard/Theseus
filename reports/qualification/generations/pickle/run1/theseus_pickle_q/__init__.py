# generation A pickle scan

def dumps(obj, protocol=0):
    if protocol != 0:
        raise ValueError("unsupported pickle protocol: %d" % (protocol,))
    return _encode(obj)


def _encode_int(n):
    return b"I" + str(n).encode("ascii") + b"\n"


def _encode_list(items):
    out = bytearray()
    out.extend(b"(lp0\n")
    for item in items:
        out.extend(_encode(item))
        out.extend(b"a")
    out.extend(b".")
    return bytes(out)


def _encode(obj):
    if type(obj) is int:
        return _encode_int(obj)
    if type(obj) is list:
        return _encode_list(obj)
    raise TypeError("can't pickle %r object" % (type(obj).__name__,))
