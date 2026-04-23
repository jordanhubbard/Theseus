"""
theseus_fnmatch_cr — Clean-room fnmatch module.
No import of the standard `fnmatch` module.
"""

import re as _re
import os


def translate(pat):
    """Translate a shell pattern to a regular expression string."""
    i = 0
    n = len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i += 1
        if c == '*':
            res += '.*'
        elif c == '?':
            res += '.'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j += 1
            if j < n and pat[j] == ']':
                j += 1
            while j < n and pat[j] != ']':
                j += 1
            if j >= n:
                res += _re.escape(c)
            else:
                stuff = pat[i:j]
                i = j + 1
                if '!' == stuff[0]:
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                stuff = stuff.replace('\\', '\\\\')
                res += '[' + stuff + ']'
        else:
            res += _re.escape(c)
    return r'(?s:%s)\Z' % res


def fnmatchcase(name, pat):
    """Test whether name matches pat (case-sensitive)."""
    return bool(_re.match(translate(pat), name))


def fnmatch(name, pat):
    """Test whether name matches pat, using OS case sensitivity."""
    if os.path is not None:
        name = os.path.normcase(name)
        pat = os.path.normcase(pat)
    return fnmatchcase(name, pat)


def filter(names, pat):
    """Return the subset of names matching pat."""
    result = []
    pat = os.path.normcase(pat)
    rx = _re.compile(translate(pat))
    for name in names:
        if rx.match(os.path.normcase(name)):
            result.append(name)
    return result


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def fnmatch2_star():
    """fnmatch('foo.txt', '*.txt') returns True."""
    return fnmatch('foo.txt', '*.txt')


def fnmatch2_question():
    """fnmatch('foo', 'f?o') returns True."""
    return fnmatch('foo', 'f?o')


def fnmatch2_filter():
    """filter(['a.py','b.txt','c.py'], '*.py') returns 2 items."""
    return len(filter(['a.py', 'b.txt', 'c.py'], '*.py'))


__all__ = [
    'fnmatch', 'fnmatchcase', 'filter', 'translate',
    'fnmatch2_star', 'fnmatch2_question', 'fnmatch2_filter',
]
