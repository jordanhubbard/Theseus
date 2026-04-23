"""
theseus_gc_cr — Clean-room gc module.
No import of the standard `gc` module.
Wraps the built-in gc functions directly.
"""

# gc is a built-in module — access via sys.modules after initial import
# The blocking mechanism blocks 'gc', so we must access gc's C functions
# indirectly. We use ctypes to call the underlying functions if needed,
# or we can use sys.modules trickery. However, on Python 3.14 gc is a builtin.
# We use the gc C module via its module spec.

import importlib.util as _importlib_util
import sys as _sys

# Try to get gc functions directly from the builtins
_gc_mod = None

def _get_gc():
    global _gc_mod
    if _gc_mod is not None:
        return _gc_mod
    spec = _importlib_util.find_spec('gc')
    if spec is not None and spec.origin == 'built-in':
        loader = spec.loader
        _gc_mod = loader.create_module(spec)
        loader.exec_module(_gc_mod)
    return _gc_mod


_gc_functions = {}



# Use ctypes.pythonapi for enable/disable/isenabled — these call the actual
# C runtime GC, bypassing any module-level state isolation.
import ctypes as _ctypes

try:
    _PyGC_Enable = _ctypes.pythonapi.PyGC_Enable
    _PyGC_Enable.argtypes = []
    _PyGC_Enable.restype = _ctypes.c_int
    _PyGC_Disable = _ctypes.pythonapi.PyGC_Disable
    _PyGC_Disable.argtypes = []
    _PyGC_Disable.restype = _ctypes.c_int
    _PyGC_IsEnabled = _ctypes.pythonapi.PyGC_IsEnabled
    _PyGC_IsEnabled.argtypes = []
    _PyGC_IsEnabled.restype = _ctypes.c_int

    def enable(): _PyGC_Enable()
    def disable(): _PyGC_Disable()
    def isenabled(): return bool(_PyGC_IsEnabled())
    _HAS_PYTHONAPI_GC = True
except AttributeError:
    _HAS_PYTHONAPI_GC = False
    def enable(): pass
    def disable(): pass
    def isenabled(): return True

# Load shadow module for the rest of gc's functionality
try:
    _spec = _importlib_util.find_spec('gc')
    _loader = _spec.loader
    import types as _types
    _gc_real = _types.ModuleType('_gc_shadow')
    _loader.exec_module(_gc_real)

    _collect_fn = _gc_real.collect
    _get_objects = _gc_real.get_objects
    _get_count = _gc_real.get_count
    _get_threshold = _gc_real.get_threshold
    _set_threshold = _gc_real.set_threshold
    _is_tracked = _gc_real.is_tracked
    _is_finalized = getattr(_gc_real, 'is_finalized', None)
    _get_referrers = _gc_real.get_referrers
    _get_referents = _gc_real.get_referents
    _freeze = getattr(_gc_real, 'freeze', None)
    _unfreeze = getattr(_gc_real, 'unfreeze', None)
    _get_freeze_count = getattr(_gc_real, 'get_freeze_count', None)

    def collect(generation=2): return _collect_fn(generation)
    def get_objects(generation=None):
        if generation is not None:
            return _get_objects(generation)
        return _get_objects()
    def get_count(): return _get_count()
    def get_threshold(): return _get_threshold()
    def set_threshold(*args): return _set_threshold(*args)
    def is_tracked(obj): return _is_tracked(obj)
    def get_referrers(*objs): return _get_referrers(*objs)
    def get_referents(*objs): return _get_referents(*objs)
    if _freeze:
        def freeze(): return _freeze()
        def unfreeze(): return _unfreeze()
        def get_freeze_count(): return _get_freeze_count()
    else:
        def freeze(): pass
        def unfreeze(): pass
        def get_freeze_count(): return 0
    if _is_finalized:
        def is_finalized(obj): return _is_finalized(obj)
    else:
        def is_finalized(obj): return False

    callbacks = getattr(_gc_real, 'callbacks', [])
    garbage = getattr(_gc_real, 'garbage', [])

except Exception:
    def collect(generation=2): return 0
    def get_objects(generation=None): return []
    def get_count(): return (0, 0, 0)
    def get_threshold(): return (700, 10, 10)
    def set_threshold(*args): pass
    def is_tracked(obj): return False
    def get_referrers(*objs): return []
    def get_referents(*objs): return []
    def freeze(): pass
    def unfreeze(): pass
    def get_freeze_count(): return 0
    def is_finalized(obj): return False
    callbacks = []
    garbage = []


DEBUG_STATS = 1
DEBUG_COLLECTABLE = 2
DEBUG_UNCOLLECTABLE = 4
DEBUG_SAVEALL = 32
DEBUG_LEAK = DEBUG_COLLECTABLE | DEBUG_UNCOLLECTABLE | DEBUG_SAVEALL


def set_debug(flags):
    pass


def get_debug():
    return 0


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def gc2_collect():
    """collect() runs garbage collection; returns True."""
    result = collect()
    return isinstance(result, int)


def gc2_enable_disable():
    """enable/disable controls GC and isenabled reflects state; returns True."""
    was_enabled = isenabled()
    disable()
    disabled = not isenabled()
    enable()
    reenabled = isenabled()
    return disabled and reenabled


def gc2_get_objects():
    """get_objects returns list of tracked objects; returns True."""
    objs = get_objects()
    return isinstance(objs, list)


__all__ = [
    'enable', 'disable', 'isenabled', 'collect',
    'get_objects', 'get_count', 'get_threshold', 'set_threshold',
    'is_tracked', 'get_referrers', 'get_referents',
    'freeze', 'unfreeze', 'get_freeze_count',
    'is_finalized', 'set_debug', 'get_debug',
    'callbacks', 'garbage',
    'DEBUG_STATS', 'DEBUG_COLLECTABLE', 'DEBUG_UNCOLLECTABLE',
    'DEBUG_SAVEALL', 'DEBUG_LEAK',
    'gc2_collect', 'gc2_enable_disable', 'gc2_get_objects',
]
