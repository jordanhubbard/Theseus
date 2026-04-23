# theseus_keyword_cr2 - Clean-room keyword utilities for Python
# Do NOT import the 'keyword' module

kwlist = [
    'False',
    'None',
    'True',
    'and',
    'as',
    'assert',
    'async',
    'await',
    'break',
    'class',
    'continue',
    'def',
    'del',
    'elif',
    'else',
    'except',
    'finally',
    'for',
    'from',
    'global',
    'if',
    'import',
    'in',
    'is',
    'lambda',
    'nonlocal',
    'not',
    'or',
    'pass',
    'raise',
    'return',
    'try',
    'while',
    'with',
    'yield',
]

softkwlist = [
    'match',
    'case',
    'type',
]

_kwset = set(kwlist)
_softkwset = set(softkwlist)


def iskeyword(s: str) -> bool:
    """Return True if s is a Python hard keyword."""
    return s in _kwset


def issoftkeyword(s: str) -> bool:
    """Return True if s is a Python soft keyword."""
    return s in _softkwset


# --- Invariant functions ---

def keyword2_softkwlist() -> bool:
    """'match' in softkwlist — returns True."""
    return 'match' in softkwlist


def keyword2_kwlist_count() -> bool:
    """len(kwlist) > 30 — returns True."""
    return len(kwlist) > 30


def keyword2_iskeyword_false() -> bool:
    """iskeyword('hello') == False — returns False (the result of iskeyword)."""
    return iskeyword('hello')


# Also export as iskeyword_false for direct access
def iskeyword_false() -> bool:
    """iskeyword('false') — returns False since 'false' is not a keyword."""
    return iskeyword('false')