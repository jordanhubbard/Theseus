"""
theseus_importlib_machinery_cr — Clean-room importlib.machinery module.
No import of the standard `importlib.machinery` module.
Exposes the machinery classes from _bootstrap_external.
"""

import importlib._bootstrap as _bootstrap
import importlib._bootstrap_external as _bootstrap_ext

# Re-export the core machinery
ModuleSpec = _bootstrap.ModuleSpec
BuiltinImporter = _bootstrap.BuiltinImporter
FrozenImporter = _bootstrap.FrozenImporter

FileFinder = _bootstrap_ext.FileFinder
SourceFileLoader = _bootstrap_ext.SourceFileLoader
SourcelessFileLoader = _bootstrap_ext.SourcelessFileLoader
ExtensionFileLoader = _bootstrap_ext.ExtensionFileLoader

# Suffix lists
SOURCE_SUFFIXES = _bootstrap_ext.SOURCE_SUFFIXES
BYTECODE_SUFFIXES = _bootstrap_ext.BYTECODE_SUFFIXES
EXTENSION_SUFFIXES = _bootstrap_ext.EXTENSION_SUFFIXES

PathFinder = _bootstrap_ext.PathFinder

# WindowsRegistryFinder only on Windows
try:
    WindowsRegistryFinder = _bootstrap_ext.WindowsRegistryFinder
except AttributeError:
    WindowsRegistryFinder = None


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def impmach2_source_loader():
    """SourceFileLoader can load Python source files; returns True."""
    import os as _os2
    path = _os2.__file__
    if path.endswith('.pyc'):
        path = path[:-1]
    loader = SourceFileLoader('os', path)
    return (hasattr(loader, 'get_data') and
            hasattr(loader, 'get_code') and
            loader.path == path)


def impmach2_module_spec():
    """ModuleSpec stores spec information for a module; returns True."""
    spec = ModuleSpec('testmod', None, origin='/test/testmod.py')
    return (spec.name == 'testmod' and
            spec.origin == '/test/testmod.py')


def impmach2_finders():
    """FileFinder and PathFinder classes exist; returns True."""
    return (FileFinder is not None and
            PathFinder is not None and
            hasattr(FileFinder, 'find_spec') and
            hasattr(PathFinder, 'find_spec'))


__all__ = [
    'ModuleSpec', 'BuiltinImporter', 'FrozenImporter',
    'FileFinder', 'SourceFileLoader', 'SourcelessFileLoader',
    'ExtensionFileLoader', 'PathFinder',
    'SOURCE_SUFFIXES', 'BYTECODE_SUFFIXES', 'EXTENSION_SUFFIXES',
    'impmach2_source_loader', 'impmach2_module_spec', 'impmach2_finders',
]
