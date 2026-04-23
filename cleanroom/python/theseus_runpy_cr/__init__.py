"""
theseus_runpy_cr — Clean-room runpy module.
No import of the standard `runpy` module.
"""

import sys as _sys
import os as _os
import importlib as _importlib
import importlib.util as _importlib_util
import importlib.machinery as _importlib_machinery
import types as _types


class _Error(Exception):
    """Internal error class for runpy."""
    pass


def _run_module_code(code, init_globals=None, mod_name=None, mod_spec=None,
                     pkg_name=None, script_name=None):
    """Execute code in a temporary module namespace."""
    fname = script_name if mod_spec is None else mod_spec.origin
    with _ModifiedArgv0(fname):
        mod_globals = _run_code(code, {}, init_globals, mod_name, mod_spec,
                                pkg_name, script_name)
    return mod_globals


def _run_code(code, run_globals, init_globals=None, mod_name=None,
              mod_spec=None, pkg_name=None, script_name=None):
    """Execute a code object in run_globals."""
    if init_globals is not None:
        run_globals.update(init_globals)

    if mod_spec is None:
        loader = None
        fname = script_name
        cached = None
    else:
        if mod_name is None:
            mod_name = mod_spec.name
        loader = mod_spec.loader
        fname = mod_spec.origin
        cached = mod_spec.cached

    run_globals.update(
        __name__=mod_name,
        __file__=fname,
        __cached__=cached,
        __doc__=None,
        __loader__=loader,
        __package__=pkg_name,
        __spec__=mod_spec,
    )
    exec(code, run_globals)
    return run_globals


class _ModifiedArgv0:
    def __init__(self, value):
        self.value = value
        self._saved_value = self  # sentinel

    def __enter__(self):
        if self.value is not None:
            self._saved_value = _sys.argv[0] if _sys.argv else None
            try:
                _sys.argv[0] = self.value
            except (AttributeError, TypeError, IndexError):
                pass

    def __exit__(self, *args):
        if self._saved_value is not self:
            try:
                _sys.argv[0] = self._saved_value
            except (AttributeError, TypeError, IndexError):
                pass


def _get_main_module_details(depth=2):
    """Helper to get details about the main module being run."""
    main_name = '__main__'
    try:
        main_module = _sys.modules[main_name]
        spec = main_module.__spec__
        if spec is not None:
            main_name = spec.name
    except KeyError:
        pass
    return main_name


def run_module(mod_name, run_name=None, alter_sys=False, init_globals=None):
    """Execute a module's code and return the resulting module globals dict."""
    mod_spec, mod_loader, pkg_name, mod_main_name = _get_module_details(mod_name)

    if run_name is None:
        run_name = mod_name

    if alter_sys:
        _sys.argv[0] = mod_spec.origin or ''

    return _run_module_code(
        mod_loader.get_code(mod_main_name),
        init_globals,
        run_name,
        mod_spec,
        pkg_name,
    )


def _get_module_details(mod_name, error=ImportError):
    """Get spec and loader for a module."""
    if mod_name.endswith('.__main__'):
        mod_name = mod_name[:-len('.__main__')]

    try:
        spec = _importlib_util.find_spec(mod_name)
    except (ImportError, AttributeError, TypeError, ValueError) as e:
        raise error(f'No module named {mod_name!r}') from e

    if spec is None:
        raise error(f'No module named {mod_name!r}')

    if spec.submodule_search_locations is not None:
        # Package — look for __main__
        main_name = mod_name + '.__main__'
        try:
            spec = _importlib_util.find_spec(main_name)
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            raise error(f'No module named {main_name!r}') from e
        if spec is None:
            raise error(f'No module named {main_name!r}; {mod_name!r} is a package')
        mod_main_name = main_name
    else:
        mod_main_name = mod_name

    pkg_name = mod_name.rpartition('.')[0]
    loader = spec.loader

    if not hasattr(loader, 'get_code'):
        loader = None

    return spec, loader, pkg_name, mod_main_name


def run_path(path_name, init_globals=None, run_name=None):
    """Execute code at the given filesystem path and return module globals."""
    if run_name is None:
        run_name = '<run_path>'

    pkg_name = run_name.rpartition('.')[0]

    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader('<run_path>', path_name)
    spec = _importlib_util.spec_from_file_location(run_name, path_name,
                                                    loader=loader)
    code = loader.get_code(run_name)
    return _run_module_code(code, init_globals, run_name, spec, pkg_name,
                            script_name=path_name)


def run_code(code, run_globals=None, init_globals=None, mod_name=None,
             mod_spec=None, pkg_name=None, script_name=None):
    """Execute code and return resulting globals dict."""
    if run_globals is None:
        run_globals = {}
    return _run_code(code, run_globals, init_globals, mod_name, mod_spec,
                     pkg_name, script_name)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def runpy2_run_module():
    """run_module() function exists and is callable; returns True."""
    return callable(run_module)


def runpy2_run_path():
    """run_path() function exists and is callable; returns True."""
    return callable(run_path)


def runpy2_run_code():
    """run_code() executes code in a namespace; returns True."""
    code = compile('x = 1 + 1', '<test>', 'exec')
    globs = run_code(code)
    return globs.get('x') == 2


__all__ = [
    'run_module', 'run_path', 'run_code',
    'runpy2_run_module', 'runpy2_run_path', 'runpy2_run_code',
]
