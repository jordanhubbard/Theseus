# generation A unquote scan

_HEX = frozenset("0123456789ABCDEFabcdef")


def unquote(string):
    if "%" not in string:
        return string
    out = bytearray()
    i = 0
    n = len(string)
    while i < n:
        if string[i] == "%" and i + 2 < n:
            a = string[i + 1]
            b = string[i + 2]
            if a in _HEX and b in _HEX:
                out.append(int(string[i + 1 : i + 3], 16))
                i += 3
                continue
        out.extend(string[i].encode("utf-8"))
        i += 1
    return bytes(out).decode("utf-8", "replace")
