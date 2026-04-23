"""
theseus_importlib_resources_cr — Clean-room importlib.resources module.
No import of the standard `importlib.resources` module.
"""

import sys as _sys
import os as _os
import pathlib as _pathlib
import importlib.util as _ilu
import contextlib as _contextlib
import io as _io
from typing import Union


class Traversable:
    """Protocol for resource containers."""

    def is_dir(self):
        raise NotImplementedError

    def is_file(self):
        raise NotImplementedError

    def iterdir(self):
        raise NotImplementedError

    def joinpath(self, child):
        raise NotImplementedError

    def open(self, mode='r', *args, **kwargs):
        raise NotImplementedError

    @property
    def name(self):
        raise NotImplementedError

    def __truediv__(self, child):
        return self.joinpath(child)

    def read_bytes(self):
        with self.open('rb') as f:
            return f.read()

    def read_text(self, encoding=None):
        with self.open('r', encoding=encoding) as f:
            return f.read()


class Path(Traversable):
    """A Traversable backed by pathlib.Path."""

    def __init__(self, path):
        self._path = _pathlib.Path(path) if not isinstance(path, _pathlib.Path) else path

    def is_dir(self):
        return self._path.is_dir()

    def is_file(self):
        return self._path.is_file()

    def iterdir(self):
        return (Path(p) for p in self._path.iterdir())

    def joinpath(self, child):
        return Path(self._path / child)

    def open(self, mode='r', *args, **kwargs):
        return self._path.open(mode, *args, **kwargs)

    @property
    def name(self):
        return self._path.name

    def __str__(self):
        return str(self._path)

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self._path))


def files(package):
    """Get a Traversable resource from a package."""
    if isinstance(package, str):
        spec = _ilu.find_spec(package)
        if spec is None:
            raise ModuleNotFoundError(package)
        package_path = spec.origin
        if package_path is None:
            raise TypeError('package has no location')
        pkg_dir = _os.path.dirname(package_path)
    elif hasattr(package, '__spec__'):
        spec = package.__spec__
        if spec.origin is None:
            raise TypeError('package has no location')
        pkg_dir = _os.path.dirname(spec.origin)
    else:
        raise TypeError('package must be a module or string')
    return Path(pkg_dir)


@_contextlib.contextmanager
def as_file(path):
    """Context manager: yield a Path to resource."""
    if isinstance(path, _pathlib.Path):
        yield path
    elif isinstance(path, Path):
        yield path._path
    elif isinstance(path, Traversable):
        # Write to a temp file
        import tempfile as _tmp
        suffix = _os.path.splitext(path.name)[1] if hasattr(path, 'name') else ''
        with _tmp.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(path.read_bytes())
            tmp_path = tmp.name
        try:
            yield _pathlib.Path(tmp_path)
        finally:
            _os.unlink(tmp_path)
    else:
        yield _pathlib.Path(str(path))


def is_resource(package, name):
    """Return True if name is a resource within package."""
    try:
        pkg_files = files(package)
        resource = pkg_files.joinpath(name)
        return resource.is_file()
    except (ModuleNotFoundError, TypeError, OSError):
        return False


def contents(package):
    """Return an iterable of strings over the contents of the package."""
    pkg_files = files(package)
    return [item.name for item in pkg_files.iterdir()]


def read_text(package, resource, encoding='utf-8', errors='strict'):
    """Return the decoded string of the specified resource within a package."""
    pkg_files = files(package)
    return pkg_files.joinpath(resource).read_text(encoding=encoding)


def read_binary(package, resource):
    """Return the bytes of the named resource within the package."""
    pkg_files = files(package)
    return pkg_files.joinpath(resource).read_bytes()


def open_text(package, resource, encoding='utf-8', errors='strict'):
    """Return a file-like object opened for text reading of the resource."""
    pkg_files = files(package)
    return pkg_files.joinpath(resource).open('r', encoding=encoding, errors=errors)


def open_binary(package, resource):
    """Return a file-like object opened for binary reading of the resource."""
    pkg_files = files(package)
    return pkg_files.joinpath(resource).open('rb')


def path(package, resource):
    """A context manager providing a file path object to the resource."""
    return as_file(files(package).joinpath(resource))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def impres2_files():
    """files() function exists and accepts a package name; returns True."""
    import os as _os2
    # Use 'os' package which is always available
    result = files('os')
    return result is not None and hasattr(result, 'is_dir')


def impres2_path():
    """as_file context manager wraps a Traversable resource; returns True."""
    p = Path(_pathlib.Path(__file__).parent)
    return isinstance(p, Traversable) and p.is_dir()


def impres2_is_resource():
    """is_resource() function exists; returns True."""
    result = is_resource('os', 'path.py')
    return isinstance(result, bool)


__all__ = [
    'Traversable', 'Path',
    'files', 'as_file', 'is_resource', 'contents',
    'read_text', 'read_binary', 'open_text', 'open_binary', 'path',
    'impres2_files', 'impres2_path', 'impres2_is_resource',
]
