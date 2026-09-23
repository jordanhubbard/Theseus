# generation A fnmatch scan

import os

__all__ = ["fnmatch", "fnmatchcase"]


def fnmatch(name, pat):
    name = os.path.normcase(name)
    pat = os.path.normcase(pat)
    return fnmatchcase(name, pat)


def fnmatchcase(name, pat):
    return _match(name, 0, pat, 0)


def _match(name, ni, pat, pi):
    plen = len(pat)
    nlen = len(name)
    while pi < plen:
        c = pat[pi]
        if c == "*":
            pi += 1
            while pi < plen and pat[pi] == "*":
                pi += 1
            if pi == plen:
                return True
            while ni <= nlen:
                if _match(name, ni, pat, pi):
                    return True
                ni += 1
            return False
        if c == "?":
            if ni >= nlen:
                return False
            ni += 1
            pi += 1
            continue
        if c == "[":
            if ni >= nlen:
                return False
            ok, pi = _charset_match(name[ni], pat, pi + 1)
            if not ok:
                return False
            ni += 1
            continue
        if ni >= nlen or name[ni] != c:
            return False
        ni += 1
        pi += 1
    return ni == nlen


def _charset_match(ch, pat, pi):
    negate = False
    if pi < len(pat) and pat[pi] in "!^":
        negate = True
        pi += 1
    matched = False
    if pi < len(pat) and pat[pi] == "]":
        if ch == "]":
            matched = True
        pi += 1
    while pi < len(pat) and pat[pi] != "]":
        if (
            pi + 2 < len(pat)
            and pat[pi + 1] == "-"
            and pat[pi + 2] != "]"
        ):
            lo = pat[pi]
            hi = pat[pi + 2]
            if lo <= ch <= hi:
                matched = True
            pi += 3
        else:
            if ch == pat[pi]:
                matched = True
            pi += 1
    if pi >= len(pat):
        return False, pi
    if negate:
        matched = not matched
    return matched, pi + 1
