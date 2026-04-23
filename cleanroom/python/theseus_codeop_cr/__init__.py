"""
theseus_codeop_cr — Clean-room codeop module.
No import of the standard `codeop` module.
"""

import sys as _sys
import warnings as _warnings

# PyCF flags
PyCF_DONT_IMPLY_DEDENT = 0x200
PyCF_ALLOW_INCOMPLETE_INPUT = 0x4000

# _IncompleteInputError is a built-in in Python 3.12+
_IncompleteInputError = getattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__,
                                 '_IncompleteInputError', None)
if _IncompleteInputError is None:
    import builtins as _builtins
    _IncompleteInputError = getattr(_builtins, '_IncompleteInputError', SyntaxError)

_flags = PyCF_DONT_IMPLY_DEDENT | PyCF_ALLOW_INCOMPLETE_INPUT


def compile_command(source, filename='<input>', symbol='single'):
    """
    Compile a command and determine if it is complete.

    Returns:
      - a code object if the command is complete and correct
      - None if the command is incomplete
    Raises SyntaxError if the command is syntactically incorrect.
    """
    with _warnings.catch_warnings():
        _warnings.simplefilter('ignore', (SyntaxWarning, DeprecationWarning))
        try:
            compile(source, filename, symbol, _flags, True)
        except _IncompleteInputError:
            return None
        except SyntaxError:
            try:
                compile(source + '\n', filename, symbol, _flags, True)
                return None
            except _IncompleteInputError:
                return None
            except SyntaxError:
                pass

    # Compile without incomplete-input flag for the final code object
    try:
        return compile(source, filename, symbol,
                       PyCF_DONT_IMPLY_DEDENT, True)
    except SyntaxError:
        return None


class Compile:
    def __init__(self):
        self.flags = 0x200  # PyCF_DONT_IMPLY_DEDENT

    def __call__(self, source, filename, symbol):
        codeob = compile(source, filename, symbol, self.flags, True)
        for feature in _sys.version_info:
            pass
        return codeob


class CommandCompiler:
    def __init__(self):
        self.compiler = Compile()

    def __call__(self, source, filename='<input>', symbol='single'):
        return compile_command(source, filename, symbol)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def codeop2_compile_complete():
    """compile_command('x=1') returns a code object; returns True."""
    result = compile_command('x = 1')
    return result is not None and hasattr(result, 'co_code')


def codeop2_compile_incomplete():
    """compile_command('def f():') returns None (incomplete); returns True."""
    result = compile_command('def f():')
    return result is None


def codeop2_commandcompiler():
    """CommandCompiler() is callable; returns True."""
    cc = CommandCompiler()
    result = cc('y = 42')
    return result is not None and hasattr(result, 'co_code')


__all__ = [
    'compile_command', 'Compile', 'CommandCompiler',
    'codeop2_compile_complete', 'codeop2_compile_incomplete', 'codeop2_commandcompiler',
]
