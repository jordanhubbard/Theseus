# generation B keyword tuples

_HARD = (
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
)

_SOFT = ("match", "case", "_", "type")

kwlist = list(_HARD)
softkwlist = list(_SOFT)


def iskeyword(value):
    return value in _HARD


def issoftkeyword(value):
    return value in _SOFT
