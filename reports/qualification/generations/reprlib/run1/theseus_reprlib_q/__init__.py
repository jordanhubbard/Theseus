# generation A limited repr

import builtins

_MAXLEVEL = 6
_MAXLIST = 6
_MAXTUPLE = 6
_MAXSTRING = 30
_FILLVALUE = '...'


def repr(obj):
    return _repr1(obj, _MAXLEVEL)


def _repr1(obj, level):
    if level <= 0:
        return _FILLVALUE
    if obj is None or isinstance(obj, (bool, int, float, complex)):
        return builtins.repr(obj)
    if isinstance(obj, str):
        return _repr_str(obj)
    if isinstance(obj, list):
        return _repr_list(obj, level)
    if isinstance(obj, tuple):
        return _repr_tuple(obj, level)
    return builtins.repr(obj)


def _repr_str(s):
    r = builtins.repr(s)
    if len(r) <= _MAXSTRING:
        return r
    quote = r[0]
    inner = r[1:-1]
    room = _MAXSTRING - 5
    head = room // 2
    tail = room - head
    return quote + inner[:head] + _FILLVALUE + inner[-tail:] + quote


def _repr_sequence(prefix, suffix, items, limit, level):
    if len(items) <= limit:
        parts = [_repr1(item, level - 1) for item in items]
        return prefix + ', '.join(parts) + suffix
    parts = [_repr1(item, level - 1) for item in items[:limit]]
    return prefix + ', '.join(parts) + ', ' + _FILLVALUE + suffix


def _repr_list(obj, level):
    return _repr_sequence('[', ']', obj, _MAXLIST, level)


def _repr_tuple(obj, level):
    if len(obj) == 1:
        inner = _repr_sequence('(', ',)', obj, _MAXTUPLE, level)
        if len(obj) <= _MAXTUPLE:
            return inner[:-1] + ',)'
        return inner
    return _repr_sequence('(', ')', obj, _MAXTUPLE, level)
