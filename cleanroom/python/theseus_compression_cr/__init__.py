"""Clean-room implementation of the theseus_compression_cr namespace package.

This is a minimal stand-in for Python 3.14+'s ``compression`` namespace
package.  It exists so that downstream Theseus packages can probe a
"compression"-shaped namespace without importing the real one.  Only the
behavioural invariants required by the spec are implemented:

    * comp2_package()  -- this module is a (namespace-style) package
    * comp2_name()     -- the module exposes its expected name
    * comp2_importable -- the module can be imported without errors

No third-party libraries are imported.  In particular the real
``compression`` package is *not* imported.
"""

from __future__ import annotations

import sys as _sys

# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------

# The canonical name a caller would use to import us.
__name_expected__ = "theseus_compression_cr"

# Make this module behave like a package even when loaded as a single file.
# A package is defined (per importlib) as a module that has a non-None
# ``__path__`` attribute.  We synthesise an empty path list so introspection
# tools recognise us as a (namespace) package without needing a directory
# layout on disk.
if not hasattr(_sys.modules[__name__], "__path__"):
    __path__ = []  # type: ignore[assignment]

__version__ = "0.0.1"
__all__ = [
    "comp2_package",
    "comp2_name",
    "comp2_importable",
]


# ---------------------------------------------------------------------------
# Invariant helpers
# ---------------------------------------------------------------------------

def comp2_package() -> bool:
    """Return ``True`` if this module looks like a package.

    A module is a package when it has a ``__path__`` attribute (this is the
    same rule importlib uses).  We always set ``__path__`` above, so this
    should return ``True`` whether the module is loaded from a directory or
    from a single ``__init__.py`` file.
    """
    mod = _sys.modules.get(__name__)
    if mod is None:
        return False
    path = getattr(mod, "__path__", None)
    return path is not None


def comp2_name() -> bool:
    """Return ``True`` if the module's name matches the expected name."""
    return __name__ == __name_expected__ or __name__.endswith(
        "." + __name_expected__
    )


def comp2_importable() -> bool:
    """Return ``True`` if this module is present in ``sys.modules``.

    By the time this function can be called the module must already have
    been imported, so the check is essentially a tautology -- but it also
    guards against the module being torn out of ``sys.modules`` after the
    fact, which is the only way "importable" could become false at runtime.
    """
    return __name__ in _sys.modules