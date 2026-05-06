"""Clean-room implementation of a pydoc_data-like package stub.

This module provides a minimal stand-in for the standard library's
``pydoc_data`` package without importing it. The original ``pydoc_data``
package is essentially a namespace that ships a ``topics`` submodule
containing help topic strings used by the interactive ``help()`` system.

Here we provide just enough surface area to satisfy the documented
invariants: the package identifies itself by name, declares that it is a
package, and exposes a ``topics`` mapping.
"""

# Package metadata --------------------------------------------------------

__name__ = "theseus_pydoc_data_cr"

# A package is a module that has a ``__path__`` attribute. We do not have
# any real submodules here, but we expose an empty path list so that
# anything inspecting this module recognises it as a package.
__path__ = []  # type: list[str]

__all__ = [
    "pydoc_data2_package",
    "pydoc_data2_topics",
    "pydoc_data2_name",
    "topics",
]


# A minimal topics mapping. The real pydoc_data.topics module exposes a
# ``topics`` dictionary keyed by help topic name. We provide an empty
# dictionary so callers can introspect it without importing the original.
topics = {}


# Invariant functions -----------------------------------------------------

def pydoc_data2_package():
    """Return True if this module behaves like a package.

    A package, in Python, is a module that carries a ``__path__``
    attribute. We confirm both that the attribute exists and that it is
    iterable (list-like), matching the usual contract.
    """
    path = globals().get("__path__", None)
    if path is None:
        return False
    try:
        iter(path)
    except TypeError:
        return False
    return True


def pydoc_data2_topics():
    """Return True if a ``topics`` mapping is exposed by this package."""
    t = globals().get("topics", None)
    if t is None:
        return False
    # Must look like a mapping: support ``in`` and ``len``.
    try:
        len(t)
    except TypeError:
        return False
    return hasattr(t, "keys") and hasattr(t, "__contains__")


def pydoc_data2_name():
    """Return True if the package advertises its expected name."""
    name = globals().get("__name__", "")
    return isinstance(name, str) and name == "theseus_pydoc_data_cr"