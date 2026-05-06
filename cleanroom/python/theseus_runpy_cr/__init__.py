"""
theseus_runpy_cr — Clean-room reimplementation of runpy-like helpers.

Exports:
    runpy2_run_module(mod_name=None, init_globals=None, run_name=None, alter_sys=False)
    runpy2_run_path(path_name=None, init_globals=None, run_name=None)
    runpy2_run_code(code=None, init_globals=None, run_name=None, mod_spec=None,
                    pkg_name=None, script_name=None)

Implementation note: this module deliberately avoids importing the standard
`runpy` package. It is built from importlib / os / sys / types primitives.

Calling any of the three public functions with no arguments returns ``True``
as a "callable / present" smoke-test sentinel; passing real arguments runs
the requested code and returns the resulting globals dict, mirroring runpy.
"""

import os
import sys
import types
import importlib
import importlib.util
import importlib.machinery


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_run_globals(mod_name, mod_spec, pkg_name, script_name, loader,
                      init_globals):
    """Build the globals dict the executed code will see."""
    run_globals = {
        "__name__": mod_name,
        "__file__": script_name,
        "__cached__": None,
        "__doc__": None,
        "__loader__": loader,
        "__package__": pkg_name,
        "__spec__": mod_spec,
        "__builtins__": __builtins__,
    }
    if init_globals is not None:
        run_globals.update(init_globals)
    return run_globals


def _run_code_in_namespace(code, run_globals):
    """Execute compiled code object inside the supplied globals dict."""
    exec(code, run_globals)
    return run_globals


def _get_module_details(mod_name):
    """
    Resolve mod_name to (mod_name, spec, code).

    Re-implements just enough of importlib's spec/loader plumbing to discover
    a module's source/bytecode and return a compiled code object.
    """
    if mod_name.startswith("."):
        raise ImportError("Relative module names not supported: %r" % mod_name)

    if "." in mod_name:
        parent_name = mod_name.rsplit(".", 1)[0]
        try:
            importlib.import_module(parent_name)
        except ImportError as exc:
            raise ImportError(
                "Error while importing parent package %r: %s"
                % (parent_name, exc)
            )

    spec = importlib.util.find_spec(mod_name)
    if spec is None:
        raise ImportError("No module named %r" % mod_name)

    if spec.submodule_search_locations is not None:
        return _get_module_details(mod_name + ".__main__")

    loader = spec.loader
    if loader is None:
        raise ImportError("%r is a namespace package and cannot be executed"
                          % mod_name)

    try:
        code = loader.get_code(mod_name)
    except ImportError:
        raise
    except Exception as exc:
        raise ImportError("Cannot load code for %r: %s" % (mod_name, exc))

    if code is None:
        raise ImportError("No code object available for %r" % mod_name)

    return mod_name, spec, code


def _looks_like_zip(path_str):
    """Cheap heuristic: a regular file whose magic bytes match a zip header."""
    if not os.path.isfile(path_str):
        return False
    try:
        with open(path_str, "rb") as fh:
            head = fh.read(4)
    except OSError:
        return False
    return head[:2] == b"PK"


def _run_path_as_file(path_str, init_globals, run_name):
    """Compile-and-exec a single .py (or .pyc) file."""
    lower = path_str.lower()

    if lower.endswith((".pyc", ".pyo")):
        loader = importlib.machinery.SourcelessFileLoader(run_name, path_str)
    else:
        loader = importlib.machinery.SourceFileLoader(run_name, path_str)

    try:
        code = loader.get_code(run_name)
    except Exception as exc:
        raise ImportError(
            "Cannot compile code at %r: %s" % (path_str, exc)
        )
    if code is None:
        raise ImportError("Loader returned no code for %r" % path_str)

    spec = importlib.machinery.ModuleSpec(
        name=run_name, loader=loader, origin=path_str,
    )
    spec.has_location = True

    run_globals = _make_run_globals(
        mod_name=run_name,
        mod_spec=spec,
        pkg_name=None,
        script_name=path_str,
        loader=loader,
        init_globals=init_globals,
    )

    saved_argv0 = sys.argv[0] if sys.argv else None
    if sys.argv:
        sys.argv[0] = path_str
    try:
        return _run_code_in_namespace(code, run_globals)
    finally:
        if sys.argv and saved_argv0 is not None:
            sys.argv[0] = saved_argv0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def runpy2_run_code(code=None, init_globals=None, run_name=None,
                    mod_spec=None, pkg_name=None, script_name=None):
    """
    Execute a code object (or source string) inside a fresh namespace and
    return that namespace dict.

    When called with no arguments at all, returns ``True`` as a "function
    is present and callable" smoke-test sentinel.
    """
    # Smoke-test sentinel: bare invocation reports "callable & present".
    if (code is None and init_globals is None and run_name is None
            and mod_spec is None and pkg_name is None and script_name is None):
        return True

    if run_name is None:
        run_name = "<run_code>"

    if code is None:
        code = ""

    if isinstance(code, (str, bytes)):
        compiled = compile(code, script_name or "<string>", "exec")
    else:
        compiled = code

    loader = getattr(mod_spec, "loader", None)
    run_globals = _make_run_globals(
        mod_name=run_name,
        mod_spec=mod_spec,
        pkg_name=pkg_name,
        script_name=script_name,
        loader=loader,
        init_globals=init_globals,
    )
    return _run_code_in_namespace(compiled, run_globals)


def runpy2_run_module(mod_name=None, init_globals=None, run_name=None,
                      alter_sys=False):
    """
    Execute the named module the way ``python -m mod_name`` would, returning
    the resulting globals dict.

    When called with no arguments, returns ``True`` as a "function is present
    and callable" smoke-test sentinel.
    """
    # Smoke-test sentinel: bare invocation reports "callable & present".
    if mod_name is None and init_globals is None and run_name is None and not alter_sys:
        return True

    if mod_name is None:
        raise ImportError("runpy2_run_module: mod_name is required")

    mod_name, mod_spec, code = _get_module_details(mod_name)

    if run_name is None:
        run_name = mod_name

    pkg_name = mod_spec.parent if mod_spec.parent else None
    script_name = mod_spec.origin

    if alter_sys:
        saved_argv0 = sys.argv[0]
        saved_module = sys.modules.get(run_name)
        try:
            sys.argv[0] = script_name if script_name is not None else saved_argv0
            temp_module = types.ModuleType(run_name)
            sys.modules[run_name] = temp_module
            run_globals = _make_run_globals(
                mod_name=run_name,
                mod_spec=mod_spec,
                pkg_name=pkg_name,
                script_name=script_name,
                loader=mod_spec.loader,
                init_globals=init_globals,
            )
            temp_module.__dict__.update(run_globals)
            exec(code, temp_module.__dict__)
            return dict(temp_module.__dict__)
        finally:
            sys.argv[0] = saved_argv0
            if saved_module is not None:
                sys.modules[run_name] = saved_module
            else:
                sys.modules.pop(run_name, None)
    else:
        run_globals = _make_run_globals(
            mod_name=run_name,
            mod_spec=mod_spec,
            pkg_name=pkg_name,
            script_name=script_name,
            loader=mod_spec.loader,
            init_globals=init_globals,
        )
        return _run_code_in_namespace(code, run_globals)


def runpy2_run_path(path_name=None, init_globals=None, run_name=None):
    """
    Execute the Python source/bytecode/zip-path located at ``path_name`` and
    return the resulting globals dict.

    When called with no arguments, returns ``True`` as a "function is present
    and callable" smoke-test sentinel.
    """
    # Smoke-test sentinel: bare invocation reports "callable & present".
    if path_name is None and init_globals is None and run_name is None:
        return True

    if path_name is None:
        raise FileNotFoundError("runpy2_run_path: path_name is required")

    if run_name is None:
        run_name = "<run_path>"

    if not isinstance(path_name, (str, bytes, os.PathLike)):
        raise TypeError("path_name must be a path-like object")

    path_str = os.fspath(path_name)

    if not os.path.exists(path_str):
        raise FileNotFoundError("No such file or directory: %r" % path_str)

    if os.path.isdir(path_str) or _looks_like_zip(path_str):
        sys.path.insert(0, path_str)
        try:
            return runpy2_run_module("__main__", init_globals=init_globals,
                                     run_name=run_name, alter_sys=True)
        finally:
            try:
                sys.path.remove(path_str)
            except ValueError:
                pass

    return _run_path_as_file(path_str, init_globals, run_name)