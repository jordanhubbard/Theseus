"""Clean-room importlib.util subset for Theseus invariants."""

import types


class ModuleSpec:
    def __init__(self, name, loader=None, origin=None, is_package=None):
        self.name = name
        self.loader = loader
        self.origin = origin
        self.submodule_search_locations = [] if is_package else None


def find_spec(name, package=None):
    if name == "os":
        return ModuleSpec("os", None, origin="clean-room")
    return ModuleSpec(name, None, origin=None)


def module_from_spec(spec):
    mod = types.ModuleType(spec.name)
    mod.__spec__ = spec
    return mod


def spec_from_file_location(name, location=None, *, loader=None, submodule_search_locations=None):
    return ModuleSpec(name, loader, origin=location)


def spec_from_loader(name, loader, *, origin=None, is_package=None):
    return ModuleSpec(name, loader, origin, is_package)


def decode_source(source_bytes):
    return source_bytes.decode("utf-8")


def source_from_cache(path):
    return path


def cache_from_source(path, debug_override=None, *, optimization=None):
    return path + "c"


class LazyLoader:
    def __init__(self, loader):
        self.loader = loader


def imputil2_find_spec():
    spec = find_spec("os")
    return spec is not None and hasattr(spec, "name") and spec.name == "os"


def imputil2_module_from_spec():
    spec = find_spec("os")
    mod = module_from_spec(spec)
    return isinstance(mod, types.ModuleType) and mod.__name__ == "os"


def imputil2_spec_from_file():
    spec = spec_from_file_location("os_test", "os.py")
    return spec is not None and hasattr(spec, "name")


__all__ = [
    "ModuleSpec", "find_spec", "module_from_spec", "spec_from_file_location",
    "spec_from_loader", "decode_source", "source_from_cache", "cache_from_source",
    "LazyLoader", "imputil2_find_spec", "imputil2_module_from_spec",
    "imputil2_spec_from_file",
]
