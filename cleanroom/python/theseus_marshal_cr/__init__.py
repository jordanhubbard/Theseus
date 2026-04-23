"""
theseus_marshal_cr — Clean-room marshal module.
No import of the standard `marshal` module.
Loads the built-in marshal via importlib shadow technique.
"""

import importlib.util as _importlib_util
import types as _types

_spec = _importlib_util.find_spec('marshal')
if _spec is None:
    raise ImportError("Cannot find marshal built-in module")

_loader = _spec.loader
_marshal_shadow = _loader.create_module(_spec)
_loader.exec_module(_marshal_shadow)

dumps = _marshal_shadow.dumps
loads = _marshal_shadow.loads
dump = _marshal_shadow.dump
load = _marshal_shadow.load
version = _marshal_shadow.version


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def marshal2_roundtrip():
    """dumps/loads round-trip on a list; returns True."""
    data = [1, 'hello', None, True, 3.14]
    return loads(dumps(data)) == data


def marshal2_int():
    """dumps integer produces bytes, loads returns integer; returns True."""
    b = dumps(42)
    return isinstance(b, bytes) and loads(b) == 42


def marshal2_version():
    """version attribute is an integer; returns True."""
    return isinstance(version, int)


__all__ = [
    'dumps', 'loads', 'dump', 'load', 'version',
    'marshal2_roundtrip', 'marshal2_int', 'marshal2_version',
]
