# generation A keyword frozenset. Python 3.9 only.

import sys

__all__ = ["iskeyword", "issoftkeyword", "kwlist", "softkwlist"]

kwlist = [
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
]

_SOFT_BY_VERSION = (
    (3, 12, ["_", "case", "match", "type"]),
    (3, 10, ["_", "case", "match"]),
)


def _softkwlist_for_interpreter():
    ver = sys.version_info
    for major, minor, names in _SOFT_BY_VERSION:
        if (ver.major, ver.minor) >= (major, minor):
            return list(names)
    return []


softkwlist = _softkwlist_for_interpreter()

_KEYWORDS = frozenset(kwlist)
_SOFT_KEYWORDS = frozenset(softkwlist)


def iskeyword(s):
    if not isinstance(s, str):
        return False
    return s in _KEYWORDS


def issoftkeyword(s):
    if not isinstance(s, str):
        return False
    return s in _SOFT_KEYWORDS
