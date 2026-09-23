# generation A quote scan

_ALWAYS_SAFE = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_.-"


def quote_plus(string):
    if not isinstance(string, str):
        raise TypeError("quote_plus() expected str")
    parts = []
    for ch in string:
        if ch == " ":
            parts.append("+")
        elif ch in _ALWAYS_SAFE:
            parts.append(ch)
        else:
            for b in ch.encode("utf-8"):
                parts.append("%%%02X" % b)
    return "".join(parts)
