"""Clean-room implementation of a tiny subset of importlib.machinery.

This module provides minimal stand-ins for a few primitives that mirror the
behaviour of importlib.machinery without importing it. The invariants only
require that three predicate functions return True, which they do once the
basic machinery types are defined and self-consistent.
"""


# ---------------------------------------------------------------------------
# ModuleSpec
# ---------------------------------------------------------------------------

class ModuleSpec:
    """A minimal ModuleSpec describing how to load a module."""

    def __init__(self, name, loader, *, origin=None, is_package=False):
        self.name = name
        self.loader = loader
        self.origin = origin
        self.submodule_search_locations = [] if is_package else None
        self.loader_state = None
        self.cached = None
        self.has_location = origin is not None

    @property
    def parent(self):
        if self.submodule_search_locations is None:
            # Not a package: parent is everything before the last dot.
            return self.name.rpartition(".")[0]
        return self.name

    def __repr__(self):
        return (
            "ModuleSpec(name=%r, loader=%r, origin=%r)"
            % (self.name, self.loader, self.origin)
        )

    def __eq__(self, other):
        if not isinstance(other, ModuleSpec):
            return NotImplemented
        return (
            self.name == other.name
            and self.loader == other.loader
            and self.origin == other.origin
            and self.submodule_search_locations
            == other.submodule_search_locations
        )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

class Loader:
    """Base loader class."""

    def create_module(self, spec):
        return None  # use default module creation

    def exec_module(self, module):
        raise NotImplementedError

    def load_module(self, fullname):
        raise NotImplementedError


class SourceLoader(Loader):
    """A loader that reads source code and executes it in a module."""

    def get_data(self, path):
        with open(path, "rb") as fh:
            return fh.read()

    def get_filename(self, fullname):
        raise NotImplementedError

    def get_source(self, fullname):
        path = self.get_filename(fullname)
        data = self.get_data(path)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1")

    def source_to_code(self, data, path="<string>"):
        if isinstance(data, (bytes, bytearray)):
            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError:
                source = data.decode("latin-1")
        else:
            source = data
        return compile(source, path, "exec")

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return None
        return self.source_to_code(source, self.get_filename(fullname))

    def exec_module(self, module):
        code = self.get_code(module.__name__)
        if code is None:
            raise ImportError("cannot load module %r" % module.__name__)
        exec(code, module.__dict__)


class _StringSourceLoader(SourceLoader):
    """A SourceLoader subclass backed by an in-memory string mapping."""

    def __init__(self, sources):
        self._sources = dict(sources)

    def get_filename(self, fullname):
        if fullname in self._sources:
            return "<string:%s>" % fullname
        raise ImportError(fullname)

    def get_source(self, fullname):
        if fullname not in self._sources:
            raise ImportError(fullname)
        return self._sources[fullname]

    def get_data(self, path):
        # path is "<string:fullname>"
        prefix = "<string:"
        if path.startswith(prefix) and path.endswith(">"):
            name = path[len(prefix):-1]
            if name in self._sources:
                return self._sources[name].encode("utf-8")
        raise OSError(path)


# ---------------------------------------------------------------------------
# Finders
# ---------------------------------------------------------------------------

class MetaPathFinder:
    """Base class for meta path finders."""

    def find_spec(self, fullname, path=None, target=None):
        return None

    def invalidate_caches(self):
        pass


class PathEntryFinder:
    """Base class for path entry finders."""

    def find_spec(self, fullname, target=None):
        return None

    def invalidate_caches(self):
        pass


class _MappingFinder(MetaPathFinder):
    """A meta-path finder backed by a {name: source_string} mapping."""

    def __init__(self, sources):
        self._sources = dict(sources)
        self._loader = _StringSourceLoader(self._sources)

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self._sources:
            return ModuleSpec(fullname, self._loader,
                              origin="<string:%s>" % fullname)
        return None


# ---------------------------------------------------------------------------
# Helpers used by invariants
# ---------------------------------------------------------------------------

def spec_from_loader(name, loader, *, origin=None, is_package=False):
    return ModuleSpec(name, loader, origin=origin, is_package=is_package)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def impmach2_source_loader():
    """SourceLoader compiles and executes source code into a module."""
    sources = {
        "demo_mod": "value = 21\nresult = value * 2\n",
    }
    loader = _StringSourceLoader(sources)

    # get_source / get_data round-trip
    src = loader.get_source("demo_mod")
    if "value = 21" not in src:
        return False
    data = loader.get_data(loader.get_filename("demo_mod"))
    if not isinstance(data, (bytes, bytearray)):
        return False
    if b"result = value * 2" not in data:
        return False

    # source_to_code produces a real code object that compiles.
    code = loader.get_code("demo_mod")
    if code is None:
        return False

    # exec_module populates the module namespace.
    class _M:
        __name__ = "demo_mod"

    module = _M()
    module.__dict__["__name__"] = "demo_mod"
    loader.exec_module(module)
    if module.__dict__.get("value") != 21:
        return False
    if module.__dict__.get("result") != 42:
        return False

    # Missing module raises ImportError.
    try:
        loader.get_source("nope")
    except ImportError:
        pass
    else:
        return False

    return True


def impmach2_module_spec():
    """ModuleSpec correctly captures name, loader, origin, and package state."""
    loader = SourceLoader()
    spec = spec_from_loader("pkg.sub", loader, origin="/tmp/pkg/sub.py")
    if spec.name != "pkg.sub":
        return False
    if spec.loader is not loader:
        return False
    if spec.origin != "/tmp/pkg/sub.py":
        return False
    if spec.submodule_search_locations is not None:
        return False
    if spec.parent != "pkg":
        return False
    if not spec.has_location:
        return False

    pkg_spec = spec_from_loader("pkg", loader, origin="/tmp/pkg/__init__.py",
                                is_package=True)
    if pkg_spec.submodule_search_locations != []:
        return False
    if pkg_spec.parent != "pkg":
        return False

    bare = ModuleSpec("solo", None)
    if bare.has_location:
        return False
    if bare.parent != "":
        return False
    if bare.submodule_search_locations is not None:
        return False

    # Equality
    other = spec_from_loader("pkg.sub", loader, origin="/tmp/pkg/sub.py")
    if spec != other:
        return False
    if spec == bare:
        return False

    return True


def impmach2_finders():
    """Finders return ModuleSpec for known names and None otherwise."""
    sources = {
        "alpha": "x = 1\n",
        "beta": "y = 2\n",
    }
    finder = _MappingFinder(sources)

    spec = finder.find_spec("alpha")
    if spec is None:
        return False
    if not isinstance(spec, ModuleSpec):
        return False
    if spec.name != "alpha":
        return False
    if not isinstance(spec.loader, SourceLoader):
        return False
    if spec.origin != "<string:alpha>":
        return False

    # Unknown module -> None
    if finder.find_spec("missing") is not None:
        return False

    # Loader actually executes via the finder's spec.
    class _Mod:
        pass

    module = _Mod()
    module.__dict__["__name__"] = "alpha"
    spec.loader.exec_module(module)
    if module.__dict__.get("x") != 1:
        return False

    # Base finders are inert but well-formed.
    base_meta = MetaPathFinder()
    if base_meta.find_spec("anything") is not None:
        return False
    base_meta.invalidate_caches()  # must not raise

    base_path = PathEntryFinder()
    if base_path.find_spec("anything") is not None:
        return False
    base_path.invalidate_caches()  # must not raise

    return True