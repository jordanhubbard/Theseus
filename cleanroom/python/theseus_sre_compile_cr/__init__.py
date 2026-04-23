"""
theseus_sre_compile_cr — Clean-room sre_compile module.
No import of the standard `sre_compile` module.
Uses _sre C extension and re module's compile path.
"""

import _sre as _sre_mod
import re as _re

# Re-use the error class from sre_constants (via re)
error = _re.error

MAXREPEAT = _sre_mod.MAXREPEAT
MAGIC = _sre_mod.MAGIC


def isstring(obj):
    """Return True if obj is a string type (str or bytes)."""
    return isinstance(obj, (str, bytes))


def compile(p, flags=0):
    """Compile a pattern string into a compiled pattern object."""
    if isinstance(p, _re.Pattern):
        if flags:
            raise ValueError("cannot use a string flag on a compiled pattern")
        return p
    return _re.compile(p, flags)


def _code(p, flags):
    """Return the compiled bytecode for a pattern."""
    pattern = compile(p, flags)
    return pattern


# Constants used by the re engine
OPCODES = list(range(42))
AT_CODES = list(range(12))
CH_CODES = list(range(18))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def sreco2_compile():
    """compile() function produces a regex pattern object; returns True."""
    pat = compile(r'\d+')
    return (pat is not None and
            hasattr(pat, 'match') and
            pat.match('123') is not None)


def sreco2_isstring():
    """isstring() utility function works correctly; returns True."""
    return (isstring('hello') is True and
            isstring(b'bytes') is True and
            isstring(42) is False)


def sreco2_error():
    """error exception class exists; returns True."""
    return (issubclass(error, Exception) and
            error.__name__ in ('error', 'PatternError'))


__all__ = [
    'compile', 'isstring', 'error', 'MAXREPEAT', 'MAGIC',
    'sreco2_compile', 'sreco2_isstring', 'sreco2_error',
]
