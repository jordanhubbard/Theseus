"""Clean-room reimplementation of a small subset of importlib.resources.

This module provides ``files``, ``path``, and ``is_resource`` style helpers
for accessing resources packaged alongside a Python module, implemented from
scratch using only the Python standard library.  It does NOT import
``importlib.resources`` or any third-party library.
"""

import os
import sys
import io
import contextlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_package(package):
    """Return an imported module object given a module or its dotted name."""
    if isinstance(package, str):
        # Import the module by name without using importlib.resources.
        # We use __import__ which is a Python builtin, not importlib.resources.
        mod = __import__(package, fromlist=['__name__'])
        return mod
    # Assume already a module-like object.
    return package


def _package_directory(package):
    """Return the on-disk directory that holds a package's resources."""
    mod = _resolve_package(package)
    # Prefer __file__ if it exists.
    file_attr = getattr(mod, '__file__', None)
    if file_attr:
        return os.path.dirname(os.path.abspath(file_attr))
    # Fall back to __path__ for namespace-style packages.
    path_attr = getattr(mod, '__path__', None)
    if path_attr:
        # __path__ may be a list-like; use the first entry.
        try:
            first = next(iter(path_attr))
        except StopIteration:
            raise FileNotFoundError(
                "package %r has an empty __path__" % (mod,))
        return os.path.abspath(first)
    raise FileNotFoundError(
        "cannot determine resource directory for %r" % (mod,))


# ---------------------------------------------------------------------------
# Traversable: a small file-system-backed Path-like wrapper
# ---------------------------------------------------------------------------

class _Traversable(object):
    """A minimal Traversable implementation backed by a filesystem path."""

    def __init__(self, base):
        self._base = os.path.abspath(base)

    # -- introspection --------------------------------------------------
    @property
    def name(self):
        return os.path.basename(self._base)

    def is_dir(self):
        return os.path.isdir(self._base)

    def is_file(self):
        return os.path.isfile(self._base)

    # -- navigation -----------------------------------------------------
    def iterdir(self):
        if not os.path.isdir(self._base):
            raise NotADirectoryError(self._base)
        for entry in sorted(os.listdir(self._base)):
            yield _Traversable(os.path.join(self._base, entry))

    def joinpath(self, *parts):
        new_path = self._base
        for part in parts:
            # Allow passing already-Traversable parts.
            if isinstance(part, _Traversable):
                part = part.name
            # Reject absolute segments to keep this confined to the package.
            if os.path.isabs(part):
                raise ValueError(
                    "cannot join an absolute path: %r" % (part,))
            new_path = os.path.join(new_path, part)
        return _Traversable(new_path)

    def __truediv__(self, other):
        return self.joinpath(other)

    # -- reading --------------------------------------------------------
    def read_bytes(self):
        with open(self._base, 'rb') as f:
            return f.read()

    def read_text(self, encoding='utf-8', errors='strict'):
        with open(self._base, 'r', encoding=encoding, errors=errors) as f:
            return f.read()

    def open(self, mode='r', *args, **kwargs):
        return open(self._base, mode, *args, **kwargs)

    # -- misc -----------------------------------------------------------
    def __fspath__(self):
        return self._base

    def __str__(self):
        return self._base

    def __repr__(self):
        return "_Traversable(%r)" % (self._base,)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def files(package):
    """Return a Traversable rooted at the package directory."""
    base = _package_directory(package)
    return _Traversable(base)


@contextlib.contextmanager
def path(package, resource):
    """Yield a filesystem path to a resource inside ``package``.

    This is a context manager so it matches the importlib.resources signature.
    For packages on the filesystem the path simply points at the file; we
    don't need to extract anything to a temp directory.
    """
    base = _package_directory(package)
    # Resource must be a simple name (no path separators) per the original
    # contract, but we accept os.path.join behavior for flexibility.
    if isinstance(resource, _Traversable):
        full = resource._base
    else:
        full = os.path.join(base, resource)
    if not os.path.isfile(full):
        raise FileNotFoundError(full)
    try:
        yield full
    finally:
        # Nothing to clean up for filesystem-backed resources.
        pass


def is_resource(package, name):
    """Return True if ``name`` is a file resource directly inside ``package``."""
    base = _package_directory(package)
    candidate = os.path.join(base, name)
    # A "resource" is a file directly contained in the package, not a dir.
    if os.sep in name or (os.altsep and os.altsep in name):
        return False
    return os.path.isfile(candidate)


def contents(package):
    """Return an iterable of names of items inside ``package``."""
    base = _package_directory(package)
    return list(sorted(os.listdir(base)))


def read_binary(package, resource):
    with path(package, resource) as p:
        with open(p, 'rb') as f:
            return f.read()


def read_text(package, resource, encoding='utf-8', errors='strict'):
    with path(package, resource) as p:
        with open(p, 'r', encoding=encoding, errors=errors) as f:
            return f.read()


def open_binary(package, resource):
    base = _package_directory(package)
    full = os.path.join(base, resource)
    return open(full, 'rb')


def open_text(package, resource, encoding='utf-8', errors='strict'):
    base = _package_directory(package)
    full = os.path.join(base, resource)
    return open(full, 'r', encoding=encoding, errors=errors)


# ---------------------------------------------------------------------------
# Invariant-check helpers used by the Theseus verification harness
# ---------------------------------------------------------------------------

def _self_directory():
    """Return the directory containing this module (used for self-tests)."""
    return os.path.dirname(os.path.abspath(__file__))


def impres2_files():
    """Verify that ``files`` returns a Traversable pointing at this package."""
    try:
        # Use this very module as the test package.
        mod = sys.modules[__name__]
        trav = files(mod)
        if not isinstance(trav, _Traversable):
            return False
        if not trav.is_dir():
            return False
        # The package directory should contain __init__.py.
        init = trav.joinpath('__init__.py')
        if not init.is_file():
            return False
        # joinpath via "/" should also work.
        also = trav / '__init__.py'
        if not also.is_file():
            return False
        # iterdir should yield at least __init__.py.
        names = [t.name for t in trav.iterdir()]
        if '__init__.py' not in names:
            return False
        return True
    except Exception:
        return False


def impres2_path():
    """Verify that ``path`` yields a usable filesystem path to a resource."""
    try:
        mod = sys.modules[__name__]
        with path(mod, '__init__.py') as p:
            if not isinstance(p, str):
                return False
            if not os.path.isfile(p):
                return False
            with open(p, 'rb') as f:
                head = f.read(64)
            if not head:
                return False
        # Missing resources should raise.
        try:
            with path(mod, '__definitely_not_there__.xyz') as _p:
                return False
        except FileNotFoundError:
            pass
        return True
    except Exception:
        return False


def impres2_is_resource():
    """Verify that ``is_resource`` correctly distinguishes files from misses."""
    try:
        mod = sys.modules[__name__]
        if not is_resource(mod, '__init__.py'):
            return False
        if is_resource(mod, '__definitely_not_there__.xyz'):
            return False
        # A path with separators should not count as a direct resource.
        if is_resource(mod, os.path.join('sub', 'file.txt')):
            return False
        return True
    except Exception:
        return False


__all__ = [
    'files',
    'path',
    'is_resource',
    'contents',
    'read_binary',
    'read_text',
    'open_binary',
    'open_text',
    'impres2_files',
    'impres2_path',
    'impres2_is_resource',
]