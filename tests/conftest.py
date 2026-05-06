"""
Pytest configuration: ensure repo root and tools/ are importable
in all test modules, regardless of how pytest resolves __file__.
"""
import sys
from pathlib import Path
import importlib.metadata
import importlib.util
import json
import re
from functools import lru_cache

import pytest

_ROOT = Path(__file__).resolve().parent.parent  # repo root (tests/ parent)
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

_SPEC_PATH_RE = re.compile(r'_build"\s*/\s*"zspecs"\s*/\s*"([^"]+\.zspec\.json)"')
_STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", ()))
_REQUIRED_DISTRIBUTIONS = {
    "test_verify_behavior_tzdata.py": ("tzdata",),
}


def _is_stdlib_module(module_name):
    root = module_name.partition(".")[0]
    return module_name in _STDLIB_MODULES or root in _STDLIB_MODULES


def _module_available(module_name):
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _distribution_available(distribution_name):
    try:
        importlib.metadata.version(distribution_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


@lru_cache(maxsize=None)
def _skip_reason_for_test_file(path_string):
    path = Path(path_string)
    if not path.name.startswith("test_verify_behavior_"):
        return None

    for distribution_name in _REQUIRED_DISTRIBUTIONS.get(path.name, ()):
        if not _distribution_available(distribution_name):
            return "optional Python distribution {!r} not installed".format(distribution_name)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    for spec_name in _SPEC_PATH_RE.findall(text):
        spec_path = _ROOT / "_build" / "zspecs" / spec_name
        if not spec_path.exists():
            continue
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        library = spec.get("library", {})
        if library.get("backend") not in ("python_module", "rust_module"):
            continue
        module_name = library.get("module_name")
        if not module_name or _is_stdlib_module(module_name):
            continue
        if not _module_available(module_name):
            return "optional Python module {!r} not installed".format(module_name)
    return None


def pytest_collection_modifyitems(config, items):
    for item in items:
        item_path = getattr(item, "path", None)
        if item_path is None:
            item_path = getattr(item, "fspath", None)
        if item_path is None:
            continue
        reason = _skip_reason_for_test_file(str(item_path))
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))
