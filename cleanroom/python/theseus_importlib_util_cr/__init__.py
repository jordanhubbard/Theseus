"""Clean-room implementation of importlib.util-like helpers.

This module provides minimal stand-ins for a few importlib.util functions
without importing importlib.util itself. The exported invariant functions
return True to signal that the corresponding capability is provided.
"""

import sys as _sys
import os as _os


class _ModuleSpec:
    """A minimal stand-in for importlib.machinery.ModuleSpec."""

    def __init__(self, name, loader=None, origin=None, is_package=False):
        self.name = name
        self.loader = loader
        self.origin = origin
        self.submodule_search_locations = [] if is_package else None
        self.has_location = origin is not None
        self.cached = None
        self.parent = name.rpartition(".")[0] if is_package else name.rpartition(".")[0]
        self._set_fileattr = origin is not None

    def __repr__(self):
        parts = ["name={0!r}".format(self.name)]
        if self.loader is not None:
            parts.append("loader={0!r}".format(self.loader))
        if self.origin is not None:
            parts.append("origin={0!r}".format(self.origin))
        return "ModuleSpec({0})".format(", ".join(parts))


class _SourceFileLoader:
    """A minimal source-file loader stand-in."""

    def __init__(self, fullname, path):
        self.name = fullname
        self.path = path

    def get_filename(self, fullname=None):
        return self.path

    def get_data(self, path):
        with open(path, "rb") as f:
            return f.read()

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = self.get_data(self.path)
        code = compile(source, self.path, "exec")
        exec(code, module.__dict__)


def find_spec(name, package=None):
    """Find the spec for a module, similar to importlib.util.find_spec.

    Returns the spec from sys.modules if available, otherwise None.
    """
    if not isinstance(name, str):
        raise TypeError("module name must be str, not {0}".format(type(name)))

    # Resolve relative imports if package is given.
    if name.startswith("."):
        if not package:
            raise ValueError(
                "{0!r} is not a relative name (no leading dot)".format(name)
            )
        level = 0
        for ch in name:
            if ch == ".":
                level += 1
            else:
                break
        bits = package.rsplit(".", level - 1) if level > 1 else [package]
        if len(bits) < level:
            raise ValueError("attempted relative import beyond top-level package")
        base = bits[0]
        name = "{0}.{1}".format(base, name[level:]) if name[level:] else base

    if name in _sys.modules:
        module = _sys.modules[name]
        if module is None:
            return None
        spec = getattr(module, "__spec__", None)
        if spec is None:
            raise ValueError("{0}.__spec__ is not set".format(name))
        return spec
    return None


def module_from_spec(spec):
    """Create a module object from a spec, similar to importlib.util.module_from_spec."""
    if spec is None:
        raise TypeError("spec must not be None")

    module = None
    loader = getattr(spec, "loader", None)
    if loader is not None and hasattr(loader, "create_module"):
        module = loader.create_module(spec)

    if module is None:
        # Fall back to a fresh module object.
        from types import ModuleType
        module = ModuleType(spec.name)

    # Set the standard module attributes from the spec.
    try:
        module.__spec__ = spec
        module.__loader__ = loader
        module.__name__ = spec.name
        if getattr(spec, "origin", None) is not None and getattr(spec, "_set_fileattr", False):
            module.__file__ = spec.origin
        if getattr(spec, "submodule_search_locations", None) is not None:
            module.__path__ = spec.submodule_search_locations
            module.__package__ = spec.name
        else:
            module.__package__ = spec.name.rpartition(".")[0]
    except Exception:
        pass

    return module


def spec_from_file_location(name, location=None, loader=None, submodule_search_locations=None):
    """Build a spec based on a file location, similar to importlib.util.spec_from_file_location."""
    if location is None and loader is None:
        return None

    if location is not None:
        location = _os.fspath(location)

    is_package = submodule_search_locations is not None
    if loader is None and location is not None:
        loader = _SourceFileLoader(name, location)

    spec = _ModuleSpec(name, loader=loader, origin=location, is_package=is_package)
    if submodule_search_locations is not None:
        spec.submodule_search_locations = list(submodule_search_locations)
    return spec


# ---------------------------------------------------------------------------
# Invariant probe functions
# ---------------------------------------------------------------------------


def imputil2_find_spec():
    """Invariant: find_spec exists and behaves correctly for known modules."""
    try:
        # 'sys' is always present in sys.modules with a __spec__.
        spec = find_spec("sys")
        if spec is None:
            # Some embedded interpreters omit __spec__; fall back to a
            # round-trip through find_spec on a synthetic module.
            return False
        if getattr(spec, "name", None) != "sys":
            return False
        # find_spec for an unknown name should return None.
        if find_spec("__theseus_definitely_not_a_module__") is not None:
            return False
        return True
    except Exception:
        return False


def imputil2_module_from_spec():
    """Invariant: module_from_spec produces a module matching the spec."""
    try:
        spec = _ModuleSpec("theseus_probe_module", loader=None, origin=None)
        module = module_from_spec(spec)
        if module is None:
            return False
        if getattr(module, "__name__", None) != "theseus_probe_module":
            return False
        if getattr(module, "__spec__", None) is not spec:
            return False
        return True
    except Exception:
        return False


def imputil2_spec_from_file():
    """Invariant: spec_from_file_location builds a spec with the given origin."""
    try:
        spec = spec_from_file_location("theseus_probe_pkg", "/tmp/theseus_probe.py")
        if spec is None:
            return False
        if getattr(spec, "name", None) != "theseus_probe_pkg":
            return False
        if getattr(spec, "origin", None) != "/tmp/theseus_probe.py":
            return False
        if getattr(spec, "loader", None) is None:
            return False
        # Package variant: submodule_search_locations should be set.
        pkg_spec = spec_from_file_location(
            "theseus_probe_pkg2",
            "/tmp/theseus_probe_pkg2/__init__.py",
            submodule_search_locations=["/tmp/theseus_probe_pkg2"],
        )
        if pkg_spec is None or pkg_spec.submodule_search_locations != [
            "/tmp/theseus_probe_pkg2"
        ]:
            return False
        return True
    except Exception:
        return False


__all__ = [
    "find_spec",
    "module_from_spec",
    "spec_from_file_location",
    "imputil2_find_spec",
    "imputil2_module_from_spec",
    "imputil2_spec_from_file",
]