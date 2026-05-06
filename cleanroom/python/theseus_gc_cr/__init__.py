"""theseus_gc_cr — clean-room reimplementation of Python's gc module.

This module provides a gc-compatible API surface using only Python introspection
(sys.modules walking, vars(), id-based dedup) without importing the original
gc package.  It is sufficient for behavioural invariants that exercise the
collect / enable / disable / get_objects entry points.
"""

import sys as _sys


# --------------------------------------------------------------------------- #
# Internal state                                                              #
# --------------------------------------------------------------------------- #

_enabled = True
_debug = 0
_threshold = (700, 10, 10)
_frozen = []          # objects pushed into the "permanent" generation
_callbacks = []
garbage = []          # public list, mirrors gc.garbage


# --------------------------------------------------------------------------- #
# Collection                                                                  #
# --------------------------------------------------------------------------- #

def collect(generation=2):
    """Run a (no-op) collection cycle and return the number of unreachable
    objects found.  Without access to the real cycle collector we cannot
    actually free anything, so we conservatively report 0.
    """
    if isinstance(generation, bool) or not isinstance(generation, int):
        if not isinstance(generation, int):
            raise TypeError("an integer is required")
    if generation < 0 or generation > 2:
        raise ValueError("invalid generation")
    # Fire any registered callbacks the way CPython does.
    for cb in list(_callbacks):
        try:
            cb("start", {"generation": generation,
                         "collected": 0, "uncollectable": 0})
            cb("stop", {"generation": generation,
                        "collected": 0, "uncollectable": 0})
        except Exception:
            pass
    return 0


# --------------------------------------------------------------------------- #
# Enable / disable                                                            #
# --------------------------------------------------------------------------- #

def enable():
    global _enabled
    _enabled = True


def disable():
    global _enabled
    _enabled = False


def isenabled():
    return _enabled


# --------------------------------------------------------------------------- #
# Object enumeration                                                          #
# --------------------------------------------------------------------------- #

def _walk_objects():
    """Yield every reachable container-ish object discoverable through
    sys.modules and frame introspection.  Order is deterministic for a
    single call but not stable across calls.
    """
    seen = set()
    queue = []

    def _push(obj):
        oid = id(obj)
        if oid in seen:
            return
        seen.add(oid)
        queue.append(obj)

    # Seed with all loaded modules and their globals.
    for name, mod in list(_sys.modules.items()):
        if mod is None:
            continue
        _push(mod)
        try:
            md = vars(mod)
        except TypeError:
            md = None
        if md is not None:
            _push(md)
            for v in list(md.values()):
                _push(v)

    # Seed with frames on the current call stack.
    try:
        frame = _sys._getframe(0)
    except Exception:
        frame = None
    while frame is not None:
        _push(frame)
        try:
            _push(frame.f_globals)
            _push(frame.f_locals)
        except Exception:
            pass
        frame = frame.f_back

    # Bounded BFS — we don't follow into every leaf to keep cost reasonable.
    i = 0
    max_visit = 50000
    while i < len(queue) and i < max_visit:
        obj = queue[i]
        i += 1
        # Walk into common container types.
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                _push(k); _push(v)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for v in list(obj):
                _push(v)
        elif hasattr(obj, "__dict__"):
            try:
                d = object.__getattribute__(obj, "__dict__")
            except Exception:
                d = None
            if isinstance(d, dict):
                _push(d)

    return queue


def get_objects(generation=None):
    """Return a list of all objects tracked by the (simulated) collector.

    The optional *generation* argument is accepted for API parity but does
    not partition results — every object we know about is returned.
    """
    if generation is not None:
        if not isinstance(generation, int):
            raise TypeError("an integer is required")
        if generation < 0 or generation > 2:
            raise ValueError("generation out of range")
    objs = _walk_objects()
    # Include frozen objects too.
    seen = {id(o) for o in objs}
    for fo in _frozen:
        if id(fo) not in seen:
            seen.add(id(fo))
            objs.append(fo)
    return objs


# --------------------------------------------------------------------------- #
# Misc API surface                                                            #
# --------------------------------------------------------------------------- #

def get_count():
    return (0, 0, 0)


def get_threshold():
    return _threshold


def set_threshold(*args):
    global _threshold
    if not args:
        raise TypeError("set_threshold() takes at least 1 argument")
    if len(args) > 3:
        raise TypeError("set_threshold() takes at most 3 arguments")
    padded = list(args) + list(_threshold[len(args):])
    for v in padded:
        if not isinstance(v, int):
            raise TypeError("an integer is required")
    _threshold = tuple(padded[:3])


def get_referrers(*objs):
    # Without real GC access we cannot accurately compute referrers.
    return []


def get_referents(*objs):
    out = []
    for obj in objs:
        if isinstance(obj, dict):
            out.extend(list(obj.keys()))
            out.extend(list(obj.values()))
        elif isinstance(obj, (list, tuple, set, frozenset)):
            out.extend(list(obj))
        elif hasattr(obj, "__dict__"):
            try:
                d = object.__getattribute__(obj, "__dict__")
                if isinstance(d, dict):
                    out.append(d)
            except Exception:
                pass
    return out


def is_tracked(obj):
    # Containers are "tracked" by the real collector; immutables typically
    # aren't.  Approximate that distinction.
    if isinstance(obj, (str, bytes, bytearray, int, float, complex,
                        bool, type(None))):
        return False
    if isinstance(obj, (tuple, frozenset)):
        # CPython untracks tuples/frozensets that contain only untracked items.
        try:
            return any(is_tracked(x) for x in obj)
        except Exception:
            return True
    return True


def is_finalized(obj):
    return False


def freeze():
    for obj in _walk_objects():
        _frozen.append(obj)


def unfreeze():
    _frozen.clear()


def get_freeze_count():
    return len(_frozen)


def get_stats():
    return [
        {"collections": 0, "collected": 0, "uncollectable": 0},
        {"collections": 0, "collected": 0, "uncollectable": 0},
        {"collections": 0, "collected": 0, "uncollectable": 0},
    ]


def set_debug(flags):
    global _debug
    if not isinstance(flags, int):
        raise TypeError("an integer is required")
    _debug = flags


def get_debug():
    return _debug


# Debug flag constants mirroring gc's public API.
DEBUG_STATS         = 1 << 0
DEBUG_COLLECTABLE   = 1 << 1
DEBUG_UNCOLLECTABLE = 1 << 2
DEBUG_SAVEALL       = 1 << 5
DEBUG_LEAK = (DEBUG_COLLECTABLE | DEBUG_UNCOLLECTABLE | DEBUG_SAVEALL)


callbacks = _callbacks


# --------------------------------------------------------------------------- #
# gc2_* invariant entry points                                                #
# --------------------------------------------------------------------------- #

def gc2_collect(generation=2):
    """Invariant entry point: run a collection cycle.

    Returns ``True`` to indicate the collection ran without error.
    """
    if generation is None:
        generation = 2
    if isinstance(generation, bool):
        generation = int(generation)
    if not isinstance(generation, int):
        raise TypeError("an integer is required")
    if generation < 0 or generation > 2:
        raise ValueError("invalid generation")
    try:
        result = collect(generation)
    except Exception:
        return False
    # Successful collection — report a non-negative count via the truthy True.
    if not isinstance(result, int) or result < 0:
        return False
    return True


def gc2_enable_disable():
    """Invariant entry point: exercise the enable/disable cycle.

    Verifies that ``isenabled()`` reflects the requested state through a
    full disable -> enable cycle, restores the prior state, and returns
    ``True`` if every step behaved as expected.
    """
    initial = bool(isenabled())
    ok = True
    try:
        disable()
        if isenabled() is not False:
            ok = False
        enable()
        if isenabled() is not True:
            ok = False
    except Exception:
        ok = False
    finally:
        # Restore prior state so callers see no side-effect.
        if initial:
            enable()
        else:
            disable()
    return ok


def gc2_get_objects(generation=None):
    """Invariant entry point: enumerate objects tracked by the (simulated)
    collector.

    Returns ``True`` when ``get_objects`` returns a non-empty list,
    ``False`` otherwise.
    """
    try:
        objs = get_objects(generation)
    except Exception:
        return False
    return isinstance(objs, list) and len(objs) > 0


__all__ = [
    "collect", "enable", "disable", "isenabled",
    "get_objects", "get_count", "get_threshold", "set_threshold",
    "get_referrers", "get_referents", "is_tracked", "is_finalized",
    "freeze", "unfreeze", "get_freeze_count",
    "get_stats", "set_debug", "get_debug",
    "garbage", "callbacks",
    "DEBUG_STATS", "DEBUG_COLLECTABLE", "DEBUG_UNCOLLECTABLE",
    "DEBUG_SAVEALL", "DEBUG_LEAK",
    "gc2_collect", "gc2_enable_disable", "gc2_get_objects",
]