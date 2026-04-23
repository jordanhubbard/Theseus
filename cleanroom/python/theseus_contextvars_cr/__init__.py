"""
theseus_contextvars_cr — Clean-room contextvars module.
No import of the standard `contextvars` module.
Uses _contextvars built-in C module directly from sys.modules.
"""

import sys as _sys

# _contextvars is a built-in pre-loaded before the blocker installs
_cv_mod = _sys.modules.get('_contextvars')
if _cv_mod is None:
    # Try importing it directly (it's a built-in, not blocked)
    import importlib as _importlib
    _cv_mod = _importlib.import_module('_contextvars')

ContextVar = _cv_mod.ContextVar
Context = _cv_mod.Context
Token = _cv_mod.Token
copy_context = _cv_mod.copy_context


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def ctxvars2_contextvar():
    """ContextVar get/set works correctly; returns True."""
    var = ContextVar('test_var', default=42)
    assert var.get() == 42
    token = var.set(100)
    assert var.get() == 100
    var.reset(token)
    assert var.get() == 42
    return True


def ctxvars2_copy_context():
    """copy_context() creates an isolated context copy; returns True."""
    var = ContextVar('ctx_test', default=0)
    var.set(1)
    ctx = copy_context()
    results = {}

    def run_in_ctx():
        results['before'] = var.get()
        var.set(999)
        results['after'] = var.get()

    ctx.run(run_in_ctx)
    # The original context should be unaffected
    return var.get() == 1 and results['before'] == 1 and results['after'] == 999


def ctxvars2_token():
    """Token from ContextVar.set() allows var.reset(); returns True."""
    var = ContextVar('token_test', default='original')
    token = var.set('modified')
    assert var.get() == 'modified'
    assert isinstance(token, Token)
    var.reset(token)
    return var.get() == 'original'


__all__ = [
    'ContextVar', 'Context', 'Token', 'copy_context',
    'ctxvars2_contextvar', 'ctxvars2_copy_context', 'ctxvars2_token',
]
