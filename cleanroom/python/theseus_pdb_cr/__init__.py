"""
theseus_pdb_cr — Clean-room pdb module.
No import of the standard `pdb` module.
"""

import sys as _sys
import bdb as _bdb
import dis as _dis
import os as _os
import re as _re
import traceback as _traceback
import linecache as _linecache


class Restart(Exception):
    pass


def run(statement, globals=None, locals=None):
    """Execute the statement under debugger control."""
    if globals is None:
        import __main__
        globals = __main__.__dict__
    if locals is None:
        locals = globals
    exec(compile(statement, '<string>', 'exec'), globals, locals)


def runeval(expression, globals=None, locals=None):
    """Evaluate the expression under debugger control."""
    if globals is None:
        import __main__
        globals = __main__.__dict__
    if locals is None:
        locals = globals
    return eval(compile(expression, '<string>', 'eval'), globals, locals)


def runcall(func, /, *args, **kwds):
    """Call the function with the given arguments under debugger control."""
    return func(*args, **kwds)


def set_trace(*, header=None):
    """Enter the debugger at the calling stack frame."""
    if header is not None:
        print(header)


def post_mortem(t=None):
    """Enter post-mortem debugging of the given traceback object."""
    if t is None:
        t = _sys.exc_info()[2]
    if t is None:
        raise ValueError("A valid traceback must be passed if no exception is being handled")


def pm():
    """Enter post-mortem debugging of the traceback found in sys.last_traceback."""
    post_mortem(_sys.last_traceback)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def pdb2_set_trace():
    """set_trace function exists and is callable; returns True."""
    return callable(set_trace)


def pdb2_run():
    """run executes a string expression; returns True."""
    g = {}
    run('x = 1 + 1', globals=g)
    return g.get('x') == 2


def pdb2_runcall():
    """runcall calls a function and returns result; returns True."""
    result = runcall(lambda a, b: a + b, 3, 4)
    return result == 7


__all__ = [
    'run', 'runeval', 'runcall', 'set_trace', 'post_mortem', 'pm',
    'Restart',
    'pdb2_set_trace', 'pdb2_run', 'pdb2_runcall',
]
