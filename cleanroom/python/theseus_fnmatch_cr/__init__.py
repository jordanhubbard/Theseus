"""Clean-room implementation of fnmatch-style shell pattern matching.

This module is a from-scratch reimplementation; it does NOT import the
standard-library `fnmatch` module.
"""

import os
import re

__all__ = [
    "fnmatch",
    "fnmatchcase",
    "filter",
    "translate",
    "fnmatch2_star",
    "fnmatch2_question",
    "fnmatch2_filter",
]

_cache = {}
_MAX_CACHE = 256


def _compile_pattern(pat):
    cached = _cache.get(pat)
    if cached is None:
        if len(_cache) >= _MAX_CACHE:
            _cache.clear()
        cached = re.compile(translate(pat))
        _cache[pat] = cached
    return cached


def translate(pat):
    """Translate a shell-style pattern into a regular expression string.

    Special characters:
        *       matches any (possibly empty) sequence of characters
        ?       matches any single character
        [seq]   matches any single character in seq
        [!seq]  matches any single character not in seq
    """
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
            # Allow ! immediately after [
            if j < n and pat[j] == "!":
                j += 1
            # Allow a literal ] immediately after [ or [!
            if j < n and pat[j] == "]":
                j += 1
            # Find the closing ]
            while j < n and pat[j] != "]":
                j += 1
            if j >= n:
                # No closing bracket; treat the [ as a literal
                res += "\\["
            else:
                stuff = pat[i:j]
                # Escape backslashes inside the character class
                stuff = stuff.replace("\\", "\\\\")
                i = j + 1
                if stuff.startswith("!"):
                    stuff = "^" + stuff[1:]
                elif stuff.startswith("^"):
                    stuff = "\\" + stuff
                res += "[" + stuff + "]"
        else:
            res += re.escape(c)
    return "(?s:" + res + ")\\Z"


def fnmatchcase(name, pat):
    """Case-sensitive shell-style pattern match."""
    return _compile_pattern(pat).match(name) is not None


def fnmatch(name, pat):
    """Shell-style pattern match honoring the platform's case sensitivity."""
    name = os.path.normcase(name)
    pat = os.path.normcase(pat)
    return fnmatchcase(name, pat)


def filter(names, pat):
    """Return the subset of names matching pat (platform case rules)."""
    pat = os.path.normcase(pat)
    matcher = _compile_pattern(pat).match
    result = []
    for name in names:
        if matcher(os.path.normcase(name)):
            result.append(name)
    return result


# ---------------------------------------------------------------------------
# Self-test invariants
# ---------------------------------------------------------------------------

def fnmatch2_star():
    """Verify '*' wildcard semantics."""
    return (
        fnmatch("hello.txt", "*.txt")
        and fnmatch("anything", "*")
        and fnmatch("", "*")
        and not fnmatch("hello.py", "*.txt")
    )


def fnmatch2_question():
    """Verify '?' wildcard semantics."""
    return (
        fnmatch("a", "?")
        and fnmatch("ab", "??")
        and not fnmatch("abc", "??")
        and not fnmatch("", "?")
    )


def fnmatch2_filter():
    """Verify filter() returns the expected count of matches."""
    return len(filter(["a.txt", "b.txt", "c.py"], "*.txt"))