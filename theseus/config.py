"""
theseus/config.py

Load config.yaml from the project root (or a given path).
Uses PyYAML if available; otherwise falls back to a minimal built-in parser
that handles the exact structure used by config.yaml.example.
"""
from __future__ import annotations
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

_DEFAULTS: dict = {
    "ai": {
        "provider": "auto",
        "openai_base_url": "http://localhost:11434/v1",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
    },
    "artifact_store": {"url": ""},
    "targets": [],
}


def load(path: Path | None = None) -> dict:
    """
    Load configuration with a two-layer merge:

      1. config.yaml       — generic defaults, checked into git
      2. config.site.yaml  — local overrides (secrets, IPs), never committed

    If *path* is given it is used as the primary config file and the site
    override is looked for alongside it (same directory, named
    ``config.site.yaml``).  If neither file exists the built-in defaults
    are returned silently.
    """
    if path is None:
        primary = _REPO_ROOT / "config.yaml"
        site    = _REPO_ROOT / "config.site.yaml"
    else:
        primary = path
        site    = path.parent / "config.site.yaml"

    cfg = _deep_merge(_DEFAULTS, {})
    for layer in (primary, site):
        if layer.exists():
            raw = _parse_yaml(layer.read_text(encoding="utf-8"))
            cfg = _deep_merge(cfg, raw)
    return cfg


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _parse_yaml(text: str) -> dict:
    """Parse config.yaml.  Tries PyYAML; falls back to built-in subset parser."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    return _parse_simple(text)


def _scalar(v: str):
    """Convert a bare YAML scalar string to a Python value."""
    if not v:
        return None
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~"):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    return v


def _strip_comment(s: str) -> str:
    """Remove trailing YAML inline comment (space + #...), preserving URLs."""
    return re.sub(r"\s+#[^'\"]*$", "", s).strip().strip('"').strip("'")


def _parse_simple(text: str) -> dict:
    """
    Minimal YAML parser for config.yaml structure:
      - top-level mapping
      - one level of nested mappings
      - top-level lists of mappings (targets:)
    """
    result: dict = {}
    top_key: str | None = None
    list_item: dict | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)

        if stripped.startswith("- "):
            rest = _strip_comment(stripped[2:])
            list_item = {}
            if top_key is not None:
                if not isinstance(result.get(top_key), list):
                    result[top_key] = []
                result[top_key].append(list_item)
            if ":" in rest:
                k, _, v = rest.partition(":")
                list_item[k.strip()] = _scalar(_strip_comment(v.strip()))
        elif ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = _strip_comment(v.strip())
            if indent == 0:
                top_key = k
                list_item = None
                if v:
                    result[k] = _scalar(v)
                else:
                    if k not in result:
                        result[k] = {}
            elif list_item is not None:
                list_item[k] = _scalar(v)
            elif top_key is not None:
                if not isinstance(result.get(top_key), dict):
                    result[top_key] = {}
                result[top_key][k] = _scalar(v)

    return result
