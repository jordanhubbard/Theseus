# Clean-room implementation of Python keyword utilities
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

_keyword_set = frozenset(kwlist)

_soft_keywords = frozenset(['match', 'case', 'type'])


def iskeyword(s):
    """Return True if s is a Python keyword."""
    return s in _keyword_set


def issoftkeyword(s):
    """Return True if s is a Python soft keyword (match, case, type)."""
    return s in _soft_keywords


def keyword_iskeyword_if():
    """Test helper: returns True if 'if' is a keyword."""
    return iskeyword('if')


def keyword_iskeyword_foo():
    """Test helper: returns False since 'foo' is not a keyword."""
    return iskeyword('foo')


def keyword_kwlist_contains_for():
    """Test helper: returns True if 'for' is in kwlist."""
    return 'for' in kwlist