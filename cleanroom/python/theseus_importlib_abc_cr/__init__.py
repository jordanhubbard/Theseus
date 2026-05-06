"""Clean-room implementation of importlib.abc-like module.

Provides minimal abstract base classes mirroring importlib.abc semantics
without importing the original module.
"""


class MetaPathFinder:
    """Abstract base class for meta path finders."""

    def find_module(self, fullname, path=None):
        return None

    def find_spec(self, fullname, path, target=None):
        return None

    def invalidate_caches(self):
        return None


class PathEntryFinder:
    """Abstract base class for path entry finders."""

    def find_module(self, fullname):
        return None

    def find_loader(self, fullname):
        return (None, [])

    def find_spec(self, fullname, target=None):
        return None

    def invalidate_caches(self):
        return None


class Finder:
    """Legacy abstract base class for finders."""

    def find_module(self, fullname, path=None):
        raise NotImplementedError


class Loader:
    """Abstract base class for loaders."""

    def create_module(self, spec):
        return None

    def load_module(self, fullname):
        raise ImportError("Loader.load_module not implemented")

    def module_repr(self, module):
        raise NotImplementedError

    def exec_module(self, module):
        raise NotImplementedError


class ResourceLoader(Loader):
    """Abstract base class for loaders that support resource access."""

    def get_data(self, path):
        raise IOError("ResourceLoader.get_data not implemented")


class InspectLoader(Loader):
    """Abstract base class for loaders that support inspection."""

    def is_package(self, fullname):
        raise ImportError("InspectLoader.is_package not implemented")

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return None
        return compile(source, "<string>", "exec", dont_inherit=True)

    def get_source(self, fullname):
        raise ImportError("InspectLoader.get_source not implemented")

    @staticmethod
    def source_to_code(data, path="<string>"):
        return compile(data, path, "exec", dont_inherit=True)

    def exec_module(self, module):
        code = self.get_code(module.__name__)
        if code is None:
            raise ImportError(
                "cannot load module {!r} when get_code() returns None".format(
                    module.__name__
                )
            )
        exec(code, module.__dict__)


class ExecutionLoader(InspectLoader):
    """Abstract base class for loaders that can execute modules."""

    def get_filename(self, fullname):
        raise ImportError("ExecutionLoader.get_filename not implemented")

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return None
        try:
            path = self.get_filename(fullname)
        except ImportError:
            path = "<string>"
        return compile(source, path, "exec", dont_inherit=True)


class FileLoader(ResourceLoader, ExecutionLoader):
    """Abstract base class partially implementing ResourceLoader and ExecutionLoader."""

    def __init__(self, fullname, path):
        self.name = fullname
        self.path = path

    def __eq__(self, other):
        return (
            self.__class__ is other.__class__
            and getattr(self, "name", None) == getattr(other, "name", None)
            and getattr(self, "path", None) == getattr(other, "path", None)
        )

    def __hash__(self):
        return hash(self.name) ^ hash(self.path)

    def get_filename(self, fullname):
        return self.path

    def get_data(self, path):
        with open(path, "rb") as fp:
            return fp.read()

    def load_module(self, fullname):
        raise ImportError("FileLoader.load_module not implemented")


class SourceLoader(ResourceLoader, ExecutionLoader):
    """Abstract base class for loading source files."""

    def path_mtime(self, path):
        raise IOError("SourceLoader.path_mtime not implemented")

    def path_stats(self, path):
        return {"mtime": self.path_mtime(path)}

    def set_data(self, path, data):
        raise IOError("SourceLoader.set_data not implemented")

    def get_source(self, fullname):
        try:
            path = self.get_filename(fullname)
        except ImportError:
            raise ImportError(
                "source not available for {!r}".format(fullname)
            )
        try:
            data = self.get_data(path)
        except OSError as exc:
            raise ImportError(
                "source not available for {!r}".format(fullname)
            ) from exc
        if isinstance(data, bytes):
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin-1")
        return data


class ResourceReader:
    """Abstract base class for resource readers."""

    def open_resource(self, resource):
        raise FileNotFoundError(resource)

    def resource_path(self, resource):
        raise FileNotFoundError(resource)

    def is_resource(self, name):
        raise FileNotFoundError(name)

    def contents(self):
        return iter(())


class Traversable:
    """Abstract base class for traversable resource objects."""

    def iterdir(self):
        raise NotImplementedError

    def read_bytes(self):
        with self.open("rb") as f:
            return f.read()

    def read_text(self, encoding=None):
        with self.open("r", encoding=encoding) as f:
            return f.read()

    def is_dir(self):
        raise NotImplementedError

    def is_file(self):
        raise NotImplementedError

    def joinpath(self, *descendants):
        raise NotImplementedError

    def __truediv__(self, child):
        return self.joinpath(child)

    def open(self, mode="r", *args, **kwargs):
        raise NotImplementedError

    @property
    def name(self):
        raise NotImplementedError


class TraversableResources(ResourceReader):
    """Resource reader implementation backed by a Traversable."""

    def files(self):
        raise NotImplementedError

    def open_resource(self, resource):
        return self.files().joinpath(resource).open("rb")

    def resource_path(self, resource):
        raise FileNotFoundError(resource)

    def is_resource(self, path):
        return self.files().joinpath(path).is_file()

    def contents(self):
        return (item.name for item in self.files().iterdir())


# --- Invariant predicate functions ---


def importlibabs2_finder():
    """Return True iff Finder/PathEntryFinder abstract bases are present."""
    return (
        isinstance(Finder, type)
        and isinstance(PathEntryFinder, type)
        and hasattr(PathEntryFinder, "find_spec")
        and hasattr(PathEntryFinder, "invalidate_caches")
    )


def importlibabs2_loader():
    """Return True iff Loader and its specializations are present."""
    return (
        isinstance(Loader, type)
        and isinstance(ResourceLoader, type)
        and isinstance(InspectLoader, type)
        and isinstance(ExecutionLoader, type)
        and isinstance(SourceLoader, type)
        and isinstance(FileLoader, type)
        and issubclass(ResourceLoader, Loader)
        and issubclass(InspectLoader, Loader)
        and issubclass(ExecutionLoader, InspectLoader)
        and hasattr(Loader, "exec_module")
        and hasattr(Loader, "create_module")
    )


def importlibabs2_meta_path_finder():
    """Return True iff MetaPathFinder abstract base is present and well-formed."""
    return (
        isinstance(MetaPathFinder, type)
        and hasattr(MetaPathFinder, "find_spec")
        and hasattr(MetaPathFinder, "find_module")
        and hasattr(MetaPathFinder, "invalidate_caches")
    )


__all__ = [
    "MetaPathFinder",
    "PathEntryFinder",
    "Finder",
    "Loader",
    "ResourceLoader",
    "InspectLoader",
    "ExecutionLoader",
    "FileLoader",
    "SourceLoader",
    "ResourceReader",
    "Traversable",
    "TraversableResources",
    "importlibabs2_finder",
    "importlibabs2_loader",
    "importlibabs2_meta_path_finder",
]