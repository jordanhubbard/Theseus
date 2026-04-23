"""
theseus_importlib_abc_cr — Clean-room importlib.abc module.
No import of the standard `importlib.abc` module.
Uses importlib._bootstrap as foundation since it's pre-loaded.
"""

import abc as _abc
import importlib.machinery as _machinery
import sys as _sys


class Finder(metaclass=_abc.ABCMeta):
    """Legacy abstract base class for import finders."""

    @_abc.abstractmethod
    def find_module(self, fullname, path=None):
        pass


class MetaPathFinder(metaclass=_abc.ABCMeta):
    """Abstract base class for import system finders."""

    def find_module(self, fullname, path):
        return None

    def find_spec(self, fullname, path, target=None):
        return None

    def invalidate_caches(self):
        pass


class PathEntryFinder(metaclass=_abc.ABCMeta):
    """Abstract base class for path-based finders."""

    def find_module(self, fullname):
        return None

    def find_loader(self, fullname):
        return None, []

    def find_spec(self, fullname, target=None):
        return None

    def invalidate_caches(self):
        pass


class Loader(metaclass=_abc.ABCMeta):
    """Abstract base class for import loaders."""

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise ImportError

    def load_module(self, fullname):
        import importlib
        return importlib.import_module(fullname)


class ResourceLoader(Loader):
    """Abstract loader that handles resources."""

    @_abc.abstractmethod
    def get_data(self, path):
        pass


class InspectLoader(Loader):
    """Abstract loader that allows for inspection."""

    def is_package(self, fullname):
        return False

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return None
        return compile(source, '<string>', 'exec')

    def get_source(self, fullname):
        return None

    def exec_module(self, module):
        code = self.get_code(module.__name__)
        if code is None:
            raise ImportError(module.__name__)
        exec(code, module.__dict__)


class ExecutionLoader(InspectLoader):
    """Abstract loader that allows execution."""

    @_abc.abstractmethod
    def get_filename(self, fullname):
        pass

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            return None
        path = self.get_filename(fullname)
        return compile(source, path, 'exec')


class FileLoader(ResourceLoader, ExecutionLoader):
    """Abstract loader for file-based modules."""

    def __init__(self, fullname, path):
        self.name = fullname
        self.path = path

    def get_filename(self, fullname):
        return self.path

    def get_data(self, path):
        with open(path, 'rb') as f:
            return f.read()

    def get_source(self, fullname):
        path = self.get_filename(fullname)
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()


class SourceLoader(FileLoader):
    """Abstract loader for source file loading."""

    def path_stats(self, path):
        import os
        st = os.stat(path)
        return {'mtime': st.st_mtime, 'size': st.st_size}

    def path_mtime(self, path):
        return self.path_stats(path)['mtime']

    def set_data(self, path, data):
        pass

    def get_code(self, fullname):
        source = self.get_source(fullname)
        if source is None:
            raise ImportError(fullname)
        path = self.get_filename(fullname)
        return compile(source, path, 'exec')

    def exec_module(self, module):
        code = self.get_code(module.__name__)
        exec(code, module.__dict__)


class Traversable(metaclass=_abc.ABCMeta):
    """An object with a subset of pathlib.Path methods suitable for reading resources."""

    @_abc.abstractmethod
    def is_dir(self):
        pass

    @_abc.abstractmethod
    def is_file(self):
        pass

    @_abc.abstractmethod
    def iterdir(self):
        pass

    @_abc.abstractmethod
    def joinpath(self, child):
        pass

    @_abc.abstractmethod
    def open(self, mode='r', *args, **kwargs):
        pass

    @_abc.abstractmethod
    def name(self):
        pass

    def __truediv__(self, child):
        return self.joinpath(child)

    def read_bytes(self):
        with self.open('rb') as f:
            return f.read()

    def read_text(self, encoding=None):
        with self.open('r', encoding=encoding) as f:
            return f.read()


class TraversableResources(ResourceLoader):
    """Abstract resources loader with Traversable support."""

    @_abc.abstractmethod
    def files(self):
        pass

    def get_data(self, path):
        return self.files().joinpath(path).read_bytes()


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def importlibabs2_finder():
    """Finder ABC exists; returns True."""
    return (isinstance(Finder, type) and
            isinstance(MetaPathFinder, type) and
            isinstance(PathEntryFinder, type))


def importlibabs2_loader():
    """Loader ABC exists; returns True."""
    return (isinstance(Loader, type) and
            isinstance(ResourceLoader, type) and
            isinstance(InspectLoader, type))


def importlibabs2_meta_path_finder():
    """MetaPathFinder ABC exists; returns True."""
    class TestFinder(MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            return None
    finder = TestFinder()
    return isinstance(finder, MetaPathFinder)


__all__ = [
    'Finder', 'MetaPathFinder', 'PathEntryFinder',
    'Loader', 'ResourceLoader', 'InspectLoader', 'ExecutionLoader',
    'FileLoader', 'SourceLoader', 'Traversable', 'TraversableResources',
    'importlibabs2_finder', 'importlibabs2_loader', 'importlibabs2_meta_path_finder',
]
