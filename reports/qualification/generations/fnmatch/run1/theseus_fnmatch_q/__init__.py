# generation A backtrack

import os
import re
import sys


def _normcase(s):
    if os.name == "nt" or sys.platform == "darwin":
        return s.lower()
    return s


def _parse_char_class(pat, start):
    """Parse fnmatch bracket expression starting at index after '['."""
    i = start
    n = len(pat)
    negated = False
    if i < n and pat[i] in "!^":
        negated = True
        i += 1
    chars = set()
    if i < n and pat[i] == "]":
        chars.add("]")
        i += 1
    while i < n:
        if pat[i] == "]":
            return negated, chars, i + 1
        if pat[i] == "\\" and i + 1 < n:
            chars.add(pat[i + 1])
            i += 2
            continue
        if i + 2 < n and pat[i + 1] == "-" and pat[i + 2] != "]":
            lo = pat[i]
            hi = pat[i + 2]
            if ord(lo) <= ord(hi):
                for code in range(ord(lo), ord(hi) + 1):
                    chars.add(chr(code))
            else:
                chars.add(lo)
                chars.add("-")
                chars.add(hi)
            i += 3
            continue
        chars.add(pat[i])
        i += 1
    return None


def _char_in_class(ch, negated, chars):
    found = ch in chars
    if negated:
        return not found
    return found


def _match(name, pat, ni, pi):
    nlen = len(name)
    plen = len(pat)
    while pi < plen:
        pc = pat[pi]
        if pc == "*":
            if pi == plen - 1:
                return True
            pi += 1
            while ni <= nlen:
                if _match(name, pat, ni, pi):
                    return True
                ni += 1
            return False
        if ni >= nlen:
            return False
        if pc == "?":
            ni += 1
            pi += 1
            continue
        if pc == "[":
            parsed = _parse_char_class(pat, pi + 1)
            if parsed is None:
                if name[ni] != "[":
                    return False
                ni += 1
                pi += 1
                continue
            negated, chars, next_pi = parsed
            if not _char_in_class(name[ni], negated, chars):
                return False
            ni += 1
            pi = next_pi
            continue
        if name[ni] != pc:
            return False
        ni += 1
        pi += 1
    return ni == nlen


def fnmatch(name, pat):
    return _match(_normcase(name), _normcase(pat), 0, 0)


def fnmatchcase(name, pat):
    return _match(name, pat, 0, 0)


def filter(names, pat):
    return [x for x in names if fnmatch(x, pat)]


def translate(pat):
    i = 0
    n = len(pat)
    res = ""
    while i < n:
        c = pat[i]
        i += 1
        if c == "*":
            res += ".*"
        elif c == "?":
            res += "."
        elif c == "[":
            j = i
            if j < n and pat[j] in "!^":
                j += 1
            if j < n and pat[j] == "]":
                j += 1
            while j < n and pat[j] != "]":
                if pat[j] == "\\" and j + 1 < n:
                    j += 2
                else:
                    j += 1
            if j >= n:
                res += re.escape("[")
            else:
                stuff = pat[i:j]
                if stuff and stuff[0] in "!^":
                    stuff = "^" + stuff[1:]
                elif stuff and stuff[0] == "^":
                    stuff = "\\" + stuff
                res += "[" + stuff + "]"
                i = j + 1
        else:
            res += re.escape(c)
    return res + r"\Z(?ms)"
