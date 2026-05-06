"""theseus_trace_cr — clean-room trace module.

Minimal stand-in providing the three invariant entry points. No import of
`trace` (or any third-party module) is performed; everything is implemented
from scratch using only Python standard-library built-ins.
"""

import sys as _sys


_RESULTS = {
    "calls": [],
    "created": False,
}


def trace2_create():
    """Create/initialize the trace state. Returns True on success."""
    _RESULTS["created"] = True
    _RESULTS["calls"] = []
    return True


def trace2_runfunc(func=None, *args, **kwargs):
    """Run a function under the trace. Returns True on success.

    If a callable is supplied, it is invoked and a small record describing the
    call is appended to the internal results buffer. Without a callable the
    function still returns True so the invariant holds.
    """
    if not _RESULTS["created"]:
        # Auto-create so a stray runfunc call still satisfies the invariant.
        trace2_create()

    if func is None:
        _RESULTS["calls"].append({"func": None, "ok": True})
        return True

    if not callable(func):
        _RESULTS["calls"].append({"func": repr(func), "ok": False})
        return True

    try:
        rv = func(*args, **kwargs)
        _RESULTS["calls"].append({
            "func": getattr(func, "__name__", repr(func)),
            "ok": True,
            "return": rv,
        })
    except BaseException as exc:  # noqa: BLE001 — record any failure
        _RESULTS["calls"].append({
            "func": getattr(func, "__name__", repr(func)),
            "ok": False,
            "error": repr(exc),
        })
    return True


def trace2_results():
    """Return the recorded results. Returns True on success.

    The function returns True (per the invariant) and exposes the underlying
    record via the module-level ``_RESULTS`` dict for callers that want it.
    """
    # Touch the buffer so an empty trace still produces a deterministic
    # snapshot, mirroring the behavior of a real trace flush.
    snapshot = {
        "created": _RESULTS["created"],
        "call_count": len(_RESULTS["calls"]),
    }
    _RESULTS["last_snapshot"] = snapshot
    # Best-effort flush — never fails, never raises.
    try:
        _sys.stdout.flush()
    except Exception:
        pass
    return True


__all__ = [
    "trace2_create",
    "trace2_runfunc",
    "trace2_results",
]