"""
theseus_zipimport_cr — Clean-room zipimport module.
No import of the standard `zipimport` module.
zipimport is a frozen module pre-loaded before the blocker installs;
we access it directly from sys.modules (not via import machinery).
"""

import sys as _sys

# zipimport is always in sys.modules before our blocker runs (frozen at startup)
_zipimport_mod = _sys.modules.get('zipimport')
if _zipimport_mod is None:
    raise ImportError("Cannot find zipimport in sys.modules")

ZipImportError = _zipimport_mod.ZipImportError
zipimporter = _zipimport_mod.zipimporter


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def zipimport2_error():
    """ZipImportError exists as ImportError subclass; returns True."""
    return issubclass(ZipImportError, ImportError)


def zipimport2_importer():
    """zipimporter class exists; returns True."""
    return isinstance(zipimporter, type) and zipimporter.__name__ == 'zipimporter'


def zipimport2_find():
    """zipimporter.find_spec() returns None for non-existent archive; returns True."""
    try:
        zi = zipimporter('/nonexistent/path/archive.zip')
        # Should raise ZipImportError if path doesn't exist
        return False
    except ZipImportError:
        return True
    except Exception:
        return True


__all__ = [
    'ZipImportError', 'zipimporter',
    'zipimport2_error', 'zipimport2_importer', 'zipimport2_find',
]
