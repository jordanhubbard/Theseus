"""
Theseus isolation blocker.

When THESEUS_BLOCKED_PACKAGE is set, any attempt to import that package
(or any of its submodules) raises ImportError with a clear diagnostic.

This file is auto-loaded by Python when PYTHONPATH includes cleanroom/python/,
because Python imports sitecustomize at startup before any user code runs.
"""
import os
import sys

_blocked = os.environ.get("THESEUS_BLOCKED_PACKAGE", "").strip()

if _blocked:
    class _Blocker:
        def find_module(self, name, path=None):
            if name == _blocked or name.startswith(_blocked + "."):
                raise ImportError(
                    f"THESEUS ISOLATION VIOLATION: attempted to import blocked "
                    f"package '{name}'. Clean-room implementations must not "
                    f"import the original package."
                )
        # Python 3.4+ finder protocol
        def find_spec(self, name, path, target=None):
            if name == _blocked or name.startswith(_blocked + "."):
                raise ImportError(
                    f"THESEUS ISOLATION VIOLATION: attempted to import blocked "
                    f"package '{name}'. Clean-room implementations must not "
                    f"import the original package."
                )
            return None

    sys.meta_path.insert(0, _Blocker())
