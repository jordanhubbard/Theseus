# generation A backslash paths

import os

__all__ = ["join", "splitdrive", "basename", "normpath"]

_altsep = "/"
_sep = "\\"
_both_seps = "/\\"


def _fspath(path):
    return os.fspath(path)


def splitdrive(p):
    p = _fspath(p)
    if len(p) >= 2:
        if p[1] == ":" and p[0] not in _both_seps:
            return p[:2], p[2:]
        if p[0] in _both_seps and p[1] in _both_seps:
            idx = 2
            nseps = 2
            while idx < len(p):
                if p[idx] in _both_seps:
                    if nseps == 1:
                        return p[:idx], p[idx:]
                    nseps -= 1
                    idx += 1
                    while idx < len(p) and p[idx] in _both_seps:
                        idx += 1
                else:
                    idx += 1
            return p, ""
    return "", p


def _isabs(p):
    p = _fspath(p)
    drive, tail = splitdrive(p)
    if drive:
        if not tail:
            return True
        return tail[0] in _both_seps
    return len(tail) > 1 and tail[0] in _both_seps and tail[1] in _both_seps


def _colon_continues(path):
    drive, tail = splitdrive(path)
    return tail == "" and path == drive


def _append(path, part):
    if path.endswith(":") and not path.endswith("::"):
        if _colon_continues(path):
            return path + part
        return path + _sep + part
    if path.endswith(_sep) or path.endswith(_altsep):
        return path + part
    return path + _sep + part


def join(path, *paths):
    path = _fspath(path)
    if not paths:
        return path
    if len(paths) > 1:
        return join(path, join(*paths))
    if not path:
        return _fspath(paths[0])
    p = _fspath(paths[0])
    if not p:
        if path.endswith(":") and not path.endswith("::"):
            if _colon_continues(path):
                return path
            return path + _sep
        if path.endswith(_sep) or path.endswith(_altsep):
            return path
        return path + _sep
    path_drive, _path_tail = splitdrive(path)
    p_drive, p_tail = splitdrive(p)
    if p[0] in _both_seps:
        if p_drive:
            return p
        return path_drive + p
    if p_drive and p_drive != path_drive:
        return p
    if _isabs(p):
        return p
    if p_drive and p_drive == path_drive:
        return _append(path, p_tail)
    return _append(path, p)


def basename(p):
    p = _fspath(p)
    _drive, p = splitdrive(p)
    i = len(p)
    while i and p[i - 1] not in _both_seps:
        i -= 1
    return p[i:]


def normpath(path):
    path = _fspath(path)
    if not path:
        return "."
    if path.startswith("\\\\.\\"):
        return path
    path = path.replace(_altsep, _sep)
    drive, path = splitdrive(path)
    prefix = ""
    if path.startswith(_sep):
        prefix = _sep
        path = path[1:]
    comps = []
    for part in path.split(_sep):
        if not part or part == ".":
            continue
        if part == "..":
            if comps and comps[-1] != "..":
                comps.pop()
            elif prefix:
                pass
            elif drive:
                if comps and comps[-1] != "..":
                    comps.pop()
                else:
                    comps.append("..")
            else:
                comps.append("..")
        else:
            comps.append(part)
    if not comps:
        if prefix:
            return drive + prefix
        if drive:
            return drive
        return "."
    return drive + prefix + _sep.join(comps)
