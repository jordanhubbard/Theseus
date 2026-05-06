"""theseus_sys_cr — clean-room reimplementation of selected sys probes.

The public surface consists of three predicate-style probes that report
``True`` when the corresponding piece of interpreter state is reachable
without importing the package being replaced (``sys``).  We obtain a
handle to the live ``sys`` module via ``os``'s own globals — ``os``
performs ``import sys`` during its own initialization, so ``os.sys``
is a valid hand-off that does not require us to issue an import.
"""

import os as _os


def _locate_sys():
    """Return the live ``sys`` module without importing it ourselves."""
    candidate = getattr(_os, "sys", None)
    if (
        candidate is not None
        and type(candidate).__name__ == "module"
        and getattr(candidate, "__name__", "") == "sys"
    ):
        return candidate

    # Defensive fallbacks — each of these stdlib modules imports ``sys``.
    for attr in ("path", "abc", "stat", "errno", "linecache", "posixpath", "ntpath"):
        owner = getattr(_os, attr, None)
        if owner is None:
            continue
        candidate = getattr(owner, "sys", None)
        if (
            candidate is not None
            and type(candidate).__name__ == "module"
            and getattr(candidate, "__name__", "") == "sys"
        ):
            return candidate

    return None


_sys = _locate_sys()


def sys2_version():
    """Return ``True`` if the running interpreter's version string is reachable."""
    if _sys is None:
        return False
    value = getattr(_sys, "version", None)
    return isinstance(value, str) and len(value) > 0


def sys2_platform():
    """Return ``True`` if the running interpreter's platform identifier is reachable."""
    if _sys is None:
        return False
    value = getattr(_sys, "platform", None)
    return isinstance(value, str) and len(value) > 0


def sys2_modules():
    """Return ``True`` if the live module registry is reachable and populated."""
    if _sys is None:
        return False
    value = getattr(_sys, "modules", None)
    return isinstance(value, dict) and len(value) > 0


__all__ = ["sys2_version", "sys2_platform", "sys2_modules"]