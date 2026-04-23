"""
theseus_compression_cr — Clean-room compression namespace package (Python 3.14+).
No import of the standard `compression` module.
This is the parent namespace package for compression submodules.
"""

__version__ = '1.0'
__all__ = []


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def comp2_package():
    """compression is a namespace package; returns True."""
    import importlib.util as _iu
    import sys as _sys
    # This module itself is the package
    mod = _sys.modules.get(__name__, None)
    return mod is not None and hasattr(mod, '__path__')


def comp2_name():
    """module __name__ is set correctly; returns True."""
    return __name__ == 'theseus_compression_cr'


def comp2_importable():
    """module can be imported without error; returns True."""
    return True
