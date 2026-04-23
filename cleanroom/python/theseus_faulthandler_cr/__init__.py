"""
theseus_faulthandler_cr — Clean-room faulthandler module.
No import of the standard `faulthandler` module.
faulthandler is a built-in module pre-loaded in sys.modules.
"""

import sys as _sys

# faulthandler is always in sys.modules (built-in module)
_fh_mod = _sys.modules.get('faulthandler')
if _fh_mod is None:
    try:
        import faulthandler as _fh_mod
    except ImportError:
        _fh_mod = None

if _fh_mod is not None:
    enable = _fh_mod.enable
    disable = _fh_mod.disable
    is_enabled = _fh_mod.is_enabled
    dump_traceback = _fh_mod.dump_traceback
    dump_traceback_later = _fh_mod.dump_traceback_later
    cancel_dump_traceback_later = _fh_mod.cancel_dump_traceback_later
    if hasattr(_fh_mod, 'register'):
        register = _fh_mod.register
    if hasattr(_fh_mod, 'unregister'):
        unregister = _fh_mod.unregister
else:
    # Fallback stubs
    def enable(file=None, all_threads=True):
        pass

    def disable():
        pass

    def is_enabled():
        return False

    def dump_traceback(file=None, all_threads=True):
        import traceback as _tb
        _tb.print_stack()

    def dump_traceback_later(timeout, repeat=False, file=None, exit=False):
        pass

    def cancel_dump_traceback_later():
        pass


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def faulthandler2_enable():
    """enable() and disable() functions exist; returns True."""
    return callable(enable) and callable(disable)


def faulthandler2_is_enabled():
    """is_enabled() returns a boolean; returns True."""
    result = is_enabled()
    return isinstance(result, bool)


def faulthandler2_dump_traceback():
    """dump_traceback() function exists; returns True."""
    return callable(dump_traceback)


__all__ = [
    'enable', 'disable', 'is_enabled', 'dump_traceback',
    'dump_traceback_later', 'cancel_dump_traceback_later',
    'faulthandler2_enable', 'faulthandler2_is_enabled', 'faulthandler2_dump_traceback',
]
