"""
theseus_importlib_util_cr — Clean-room importlib.util module.
No import of the standard `importlib.util` module.
Delegates to _bootstrap and _bootstrap_external internals.
"""

import importlib._bootstrap as _bootstrap
import importlib._bootstrap_external as _bootstrap_external
import sys as _sys
import types as _types


def find_spec(name, package=None):
    """Find the spec for a module, optionally relative to a package."""
    if name.startswith('.'):
        if not package:
            raise TypeError('the package argument is required to perform a '
                            'relative import for {!r}'.format(name))
        for character in name:
            if character != '.':
                break
        name = _resolve_name(name, package, name.count('.'))
    return _bootstrap._find_spec(name, None, None)


def _resolve_name(name, package, level):
    """Resolve a relative module name to an absolute one."""
    bits = package.rsplit('.', level - 1)
    if len(bits) < level:
        raise ImportError('attempted relative import beyond top-level package')
    base = bits[0]
    return f'{base}.{name.lstrip(".")}' if name.lstrip('.') else base


def module_from_spec(spec):
    """Create a new module based on spec and spec.loader.create_module."""
    module = None
    if hasattr(spec.loader, 'create_module'):
        module = spec.loader.create_module(spec)
    if module is None:
        module = _types.ModuleType(spec.name)
    _init_module_attrs(spec, module)
    return module


def _init_module_attrs(spec, module, *, override=False):
    """Set module attributes from a module spec."""
    if override or not hasattr(module, '__name__'):
        module.__name__ = spec.name
    if override or not hasattr(module, '__loader__'):
        module.__loader__ = spec.loader
    if spec.submodule_search_locations is not None:
        if override or not hasattr(module, '__path__'):
            module.__path__ = spec.submodule_search_locations
    if override or not hasattr(module, '__package__'):
        module.__package__ = spec.parent
    if override or not hasattr(module, '__spec__'):
        module.__spec__ = spec
    if spec.has_location:
        if override or not hasattr(module, '__file__'):
            module.__file__ = spec.origin
        if spec.cached is not None:
            if override or not hasattr(module, '__cached__'):
                module.__cached__ = spec.cached
    return module


def spec_from_file_location(name, location=None, *, loader=None,
                             submodule_search_locations=_bootstrap._NEEDS_LOADING):
    """Return a ModuleSpec for a module located at the given path."""
    spec = _bootstrap_external.spec_from_file_location(
        name, location, loader=loader,
        submodule_search_locations=submodule_search_locations)
    return spec


def spec_from_loader(name, loader, *, origin=None, is_package=None):
    """Return a ModuleSpec based on a loader."""
    if hasattr(loader, 'get_filename'):
        if is_package is None:
            return _bootstrap_external.spec_from_file_location(name, loader=loader)
    if is_package:
        search = []
    else:
        search = None
    spec = _bootstrap.ModuleSpec(name, loader, origin=origin)
    spec.submodule_search_locations = search
    return spec


def decode_source(source_bytes):
    """Decode bytes representing source code and return the string."""
    import tokenize as _tok
    source_bytes_readline = _tok.detect_encoding(
        _io.BytesIO(source_bytes).readline)
    encoding = source_bytes_readline[0]
    newline_decoder = _io.IncrementalNewlineDecoder(None, translate=True)
    return newline_decoder.decode(source_bytes.decode(encoding))


def source_from_cache(path):
    """Given the path to a .pyc. file, return the path to its .py file."""
    if _bootstrap_external._path_isabs(path):
        pass
    head, tail = _bootstrap_external._path_split(path)
    base, ext = _bootstrap_external._path_splitext(tail)
    if ext not in _bootstrap_external._BYTECODE_SUFFIXES:
        raise ValueError(f'{path!r} is not a bytecode file')
    base_path = _bootstrap_external._path_join(head, base)
    for suffix in _bootstrap_external._SOURCE_SUFFIXES:
        init_filename = base_path + suffix
        if _bootstrap_external._path_isfile(init_filename):
            return init_filename
    return base_path + '.py'


def cache_from_source(path, debug_override=None, *, optimization=None):
    """Given the path to a .py file, return the path to its .pyc file."""
    return _bootstrap_external.cache_from_source(path, debug_override,
                                                   optimization=optimization)


class LazyLoader:
    """A loader that defers the execution of the module."""

    def __init__(self, loader):
        self.loader = loader

    @classmethod
    def factory(cls, loader):
        def f(*args, **kwargs):
            return cls(loader(*args, **kwargs))
        return f

    def create_module(self, spec):
        return self.loader.create_module(spec)

    def exec_module(self, module):
        loader = self.loader
        spec = module.__spec__

        def __getattr__(name):
            loader.exec_module(module)
            type(module).__getattr__ = None
            return getattr(module, name)

        module.__class__ = type(
            'LazyModule',
            (type(module),),
            {'__getattr__': __getattr__}
        )


# For spec_from_file_location to work, import io
import io as _io


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def imputil2_find_spec():
    """find_spec() locates a module by name; returns True."""
    spec = find_spec('os')
    return (spec is not None and
            hasattr(spec, 'name') and
            spec.name == 'os')


def imputil2_module_from_spec():
    """module_from_spec() creates a module from a spec; returns True."""
    spec = find_spec('os')
    if spec is None:
        return False
    mod = module_from_spec(spec)
    return (isinstance(mod, _types.ModuleType) and
            mod.__name__ == 'os')


def imputil2_spec_from_file():
    """spec_from_file_location() creates a spec from a file path; returns True."""
    import os as _os2
    path = _os2.__file__
    if path.endswith('.pyc'):
        path = path[:-1]
    spec = spec_from_file_location('os_test', path)
    return (spec is not None and
            hasattr(spec, 'name'))


__all__ = [
    'find_spec', 'module_from_spec', 'spec_from_file_location',
    'spec_from_loader', 'decode_source', 'source_from_cache',
    'cache_from_source', 'LazyLoader',
    'imputil2_find_spec', 'imputil2_module_from_spec', 'imputil2_spec_from_file',
]
