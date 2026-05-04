"""Clean-room importlib.machinery subset for Theseus invariants."""


class ModuleSpec:
    def __init__(self, name, loader, *, origin=None, is_package=None):
        self.name = name
        self.loader = loader
        self.origin = origin
        self.submodule_search_locations = [] if is_package else None


class SourceFileLoader:
    def __init__(self, name, path):
        self.name = name
        self.path = path

    def get_data(self, path):
        with open(path, "rb") as f:
            return f.read()

    def get_code(self, fullname):
        return None


class FileFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        return None


class PathFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        return None


def impmach2_source_loader():
    loader = SourceFileLoader("os", "os.py")
    return hasattr(loader, "get_data") and hasattr(loader, "get_code") and loader.path == "os.py"


def impmach2_module_spec():
    spec = ModuleSpec("testmod", None, origin="/test/testmod.py")
    return spec.name == "testmod" and spec.origin == "/test/testmod.py"


def impmach2_finders():
    return FileFinder is not None and PathFinder is not None and hasattr(FileFinder, "find_spec") and hasattr(PathFinder, "find_spec")


__all__ = [
    "ModuleSpec", "SourceFileLoader", "FileFinder", "PathFinder",
    "impmach2_source_loader", "impmach2_module_spec", "impmach2_finders",
]
