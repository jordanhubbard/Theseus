"""
theseus_importlib_cr — Clean-room importlib module.
No import of the standard `importlib` module.
Uses Python's built-in import machinery directly.
"""

import sys as _sys
import types as _types


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import.
    """
    level = 0
    if name.startswith('.'):
        if not package:
            msg = ("the 'package' argument is required to perform a "
                   "relative import for {!r}")
            raise TypeError(msg.format(name))
        for character in name:
            if character != '.':
                break
            level += 1
    return _bootstrap_import(name[level:], globals(), {}, [], level, package)


def _bootstrap_import(name, globs, locs, fromlist, level, package):
    """Internal import using __import__ builtin."""
    if level == 0:
        # Absolute import
        module = __import__(name, globs, locs, fromlist, 0)
        if fromlist:
            return module
        # Return top-level package for 'import a.b.c' style
        components = name.split('.')
        mod = module
        for comp in components[1:]:
            try:
                mod = getattr(mod, comp)
            except AttributeError:
                # Module may not have the attr yet; try sys.modules
                full = '.'.join(components[:components.index(comp) + 1])
                mod = _sys.modules.get(full, mod)
        return _sys.modules.get(name, module)
    else:
        # Relative import
        if package is None:
            package = globs.get('__package__') or globs.get('__name__')
        parts = package.rsplit('.', level - 1)
        if len(parts) < level:
            raise ImportError('attempted relative import beyond top-level package')
        base = parts[0]
        if name:
            full_name = base + '.' + name
        else:
            full_name = base
        return __import__(full_name, globs, locs, fromlist, 0)


def invalidate_caches():
    """Call the invalidate_caches() method on all finders in sys.meta_path."""
    for finder in _sys.meta_path:
        if hasattr(finder, 'invalidate_caches'):
            try:
                finder.invalidate_caches()
            except ImportError:
                pass  # skip finders that trigger blocked imports
    if hasattr(_sys, 'path_importer_cache'):
        _sys.path_importer_cache.clear()


def reload(module):
    """Reload the module and return it.

    The module must have been successfully imported before.
    """
    if not isinstance(module, _types.ModuleType):
        raise TypeError("reload() argument must be a module")
    name = module.__name__
    if name not in _sys.modules:
        msg = "module {!r} is not in sys.modules"
        raise ImportError(msg.format(name), name=name)

    # Get the module's spec if available
    spec = getattr(module, '__spec__', None)
    if spec is not None and hasattr(spec, 'loader'):
        loader = spec.loader
        if hasattr(loader, 'exec_module'):
            loader.exec_module(module)
            return module

    # Fallback: re-execute the module's file
    filename = getattr(module, '__file__', None)
    if filename is None:
        raise ImportError(f"cannot reload {name!r}: no __file__", name=name)

    if filename.endswith('.pyc'):
        filename = filename[:-1]

    with open(filename) as f:
        source = f.read()

    code = compile(source, filename, 'exec')
    exec(code, module.__dict__)
    return module


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def importlib2_import():
    """import_module() imports a stdlib module; returns True."""
    m = import_module('os.path')
    return m is not None and hasattr(m, 'join')


def importlib2_invalidate():
    """invalidate_caches() runs without error; returns True."""
    invalidate_caches()
    return True


def importlib2_reload():
    """reload() can reload an already-imported module; returns True."""
    import os as _os
    m = reload(_os)
    return m is _os and hasattr(m, 'getcwd')


__all__ = [
    'import_module', 'invalidate_caches', 'reload',
    'importlib2_import', 'importlib2_invalidate', 'importlib2_reload',
]
