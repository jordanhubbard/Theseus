# generation A mode scan

_IFDIR = 0o040000
_IFREG = 0o100000
_IFMT = 0o170000


def filemode(mode):
    file_type = mode & _IFMT
    if file_type == _IFREG:
        typechar = "-"
    elif file_type == _IFDIR:
        typechar = "d"
    else:
        typechar = "?"

    perm = mode & 0o777
    out = [typechar]
    for shift in (6, 3, 0):
        triple = (perm >> shift) & 7
        out.append("r" if triple & 4 else "-")
        out.append("w" if triple & 2 else "-")
        out.append("x" if triple & 1 else "-")
    return "".join(out)
