# generation A slash paths

_sep = "/"


def join(a, *paths):
    path = a
    for b in paths:
        if b.startswith(_sep):
            path = b
        elif not path or path.endswith(_sep):
            path = path + b
        else:
            path = path + _sep + b
    return path


def basename(p):
    i = len(p) - 1
    while i >= 0 and p[i] == _sep:
        i -= 1
    if i < 0:
        return ""
    end = i + 1
    while i >= 0 and p[i] != _sep:
        i -= 1
    return p[i + 1 : end]


def normpath(path):
    if not path:
        return "."
    initial_slashes = path.startswith(_sep)
    comps = []
    for comp in path.split(_sep):
        if comp in ("", "."):
            continue
        if comp == "..":
            if comps and comps[-1] != "..":
                comps.pop()
            elif not initial_slashes:
                comps.append("..")
            continue
        comps.append(comp)
    if not comps:
        return _sep if initial_slashes else "."
    joined = _sep.join(comps)
    if initial_slashes:
        joined = _sep + joined
    return joined


def splitext(p):
    if p.endswith(_sep):
        return p, ""
    sep_index = -1
    dot_index = -1
    for i in range(len(p) - 1, -1, -1):
        if p[i] == _sep:
            sep_index = i
            break
        if p[i] == "." and dot_index < 0:
            dot_index = i
    if dot_index <= sep_index or dot_index < 0:
        return p, ""
    if dot_index == 0:
        return p, ""
    return p[:dot_index], p[dot_index:]
