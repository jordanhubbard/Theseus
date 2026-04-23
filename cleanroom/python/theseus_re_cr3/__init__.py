"""Clean-room extended regex utilities. No import of re."""

from theseus_re_cr2 import compile as _compile


def fullmatch(pattern, string, flags=0):
    anchored = '^' + pattern + '$'
    m = _compile(anchored).match(string)
    if m is None:
        return None
    if m.group(0) == string:
        return m
    return None


def escape(pattern):
    _special = set(r'\.^$*+?{}[]|()')
    result = []
    for c in pattern:
        if c in _special:
            result.append('\\' + c)
        else:
            result.append(c)
    return ''.join(result)


def split(pattern, string, maxsplit=0):
    return _compile(pattern).split(string)


def re3_fullmatch():
    return fullmatch('[0-9]+', '123') is not None


def re3_escape():
    return escape('a.b')


def re3_split():
    return split('[,;]', 'a,b;c')


__all__ = ['fullmatch', 'escape', 'split']
