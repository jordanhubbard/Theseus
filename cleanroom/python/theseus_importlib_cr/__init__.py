"""Clean-room implementation of a minimal importlib-style module.

Provides import, invalidate (caches), and reload functionality
without importing the original ``importlib`` package.
"""

import sys


def importlib2_import(name=None, package=None):
    """Import a module by dotted name and return True on success.

    If ``name`` is omitted, this is a no-op that simply reports success.
    Relative imports (names beginning with '.') are resolved against
    ``package`` when provided.
    """
    if name is None:
        return True

    # Resolve relative imports.
    if isinstance(name, str) and name.startswith("."):
        if not package:
            raise TypeError(
                "the 'package' argument is required to perform a relative "
                "import for %r" % name
            )
        # Count leading dots.
        level = 0
        for ch in name:
            if ch == ".":
                level += 1
            else:
                break
        bits = package.rsplit(".", level - 1) if level > 1 else [package]
        if len(bits) < level:
            raise ValueError("attempted relative import beyond top-level package")
        base = bits[0]
        tail = name[level:]
        absolute = base + (("." + tail) if tail else "")
    else:
        absolute = name

    # If already imported, just return True.
    if absolute in sys.modules and sys.modules[absolute] is not None:
        return True

    # Use the built-in __import__ machinery (this is a builtin, not the
    # importlib package, so it is permitted under the clean-room rules).
    try:
        __import__(absolute)
    except Exception:
        raise

    return True


def importlib2_invalidate():
    """Invalidate cached finder state.

    Walks ``sys.meta_path`` and ``sys.path_importer_cache`` and asks each
    finder to drop any cached lookups, mirroring ``importlib.invalidate_caches``.
    Returns True.
    """
    # Meta path finders.
    for finder in list(sys.meta_path):
        invalidate = getattr(finder, "invalidate_caches", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                # Best-effort: a misbehaving finder must not break the call.
                pass

    # Path importer cache finders.
    cache = getattr(sys, "path_importer_cache", None)
    if isinstance(cache, dict):
        for finder in list(cache.values()):
            invalidate = getattr(finder, "invalidate_caches", None)
            if callable(invalidate):
                try:
                    invalidate()
                except Exception:
                    pass

    return True


def importlib2_reload(module=None):
    """Reload a previously imported module and return True.

    If ``module`` is None, this is a no-op success. Otherwise the module
    must be present in ``sys.modules``; its loader (or, lacking that, the
    fallback ``__import__`` machinery) is asked to repopulate the existing
    module object so that any references held elsewhere stay valid.
    """
    if module is None:
        return True

    name = getattr(module, "__name__", None)
    if not isinstance(name, str):
        raise TypeError("reload() argument must be a module")

    if sys.modules.get(name) is not module:
        raise ImportError(
            "module %s not in sys.modules" % name, name=name
        )

    # Reload parent package first if this is a submodule, to keep
    # parent.__dict__ consistent with what we are about to put back.
    parent_name = name.rpartition(".")[0]
    if parent_name and parent_name not in sys.modules:
        raise ImportError(
            "parent %r not in sys.modules during reload of %r"
            % (parent_name, name),
            name=name,
        )

    spec = getattr(module, "__spec__", None)
    loader = None
    if spec is not None:
        loader = getattr(spec, "loader", None)
    if loader is None:
        loader = getattr(module, "__loader__", None)

    # Prefer a loader.exec_module style reload when available.
    exec_module = getattr(loader, "exec_module", None)
    if callable(exec_module):
        try:
            exec_module(module)
        except Exception:
            # On failure, leave sys.modules entry as-is (matches CPython).
            raise
        # Refresh sys.modules to whatever the loader registered (some
        # loaders replace the module object during exec_module).
        if name in sys.modules:
            return True
        sys.modules[name] = module
        return True

    # Legacy load_module path.
    load_module = getattr(loader, "load_module", None)
    if callable(load_module):
        new_mod = load_module(name)
        # Mirror attributes back onto the original module object so that
        # outside references continue to see the reloaded contents.
        try:
            for key, value in list(new_mod.__dict__.items()):
                module.__dict__[key] = value
            sys.modules[name] = module
        except Exception:
            sys.modules[name] = new_mod
        return True

    # No loader at all — fall back to a fresh __import__ pass.
    saved = sys.modules.pop(name, None)
    try:
        __import__(name)
    except Exception:
        if saved is not None:
            sys.modules[name] = saved
        raise

    fresh = sys.modules.get(name)
    if fresh is not None and fresh is not module:
        try:
            for key, value in list(fresh.__dict__.items()):
                module.__dict__[key] = value
            sys.modules[name] = module
        except Exception:
            pass

    return True


__all__ = [
    "importlib2_import",
    "importlib2_invalidate",
    "importlib2_reload",
]