"""
theseus_fnmatch_q — Clean-room UNIX shell-style filename matching.
Do NOT import fnmatch.
"""

import os
import re


def translate(pat):
    """Convert a shell pattern to a regular expression (anchored)."""
    i = 0
    n = len(pat)
    out = ["\\A"]
    while i < n:
        c = pat[i]
        i += 1
        if c == "*":
            out.append(".*")
        elif c == "?":
            out.append(".")
        elif c == "[":
            j = i
            if j < n and pat[j] == "!":
                j += 1
            if j < n and pat[j] == "]":
                j += 1
            while j < n and pat[j] != "]":
                j += 1
            if j >= n:
                out.append("\\[")
            else:
                stuff = pat[i:j]
                if stuff:
                    if stuff[0] == "!":
                        stuff = "^" + stuff[1:]
                    elif stuff[0] == "^":
                        stuff = "\\" + stuff
                    out.append("[" + stuff + "]")
                i = j + 1
        else:
            out.append(re.escape(c))
    out.append("\\Z")
    return "".join(out)


def fnmatchcase(name, pat):
    return re.match(translate(pat), name, flags=re.DOTALL) is not None


def fnmatch(name, pat):
    if os.name == "nt":
        return fnmatchcase(name.lower(), pat.lower())
    return fnmatchcase(name, pat)


def filter(names, pat):
    return [n for n in names if fnmatch(n, pat)]


__all__ = ["fnmatch", "fnmatchcase", "filter", "translate"]
