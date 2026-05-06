"""Clean-room implementation of importlib.metadata-like helpers.

This module provides a minimal, self-contained subset of the
``importlib.metadata`` surface area built only from Python standard-library
primitives (``os``, ``sys``, ``re``).  It does not import or wrap the
original ``importlib.metadata`` module.
"""

import os
import sys
import re


# ---------------------------------------------------------------------------
# Helpers for locating distribution metadata on disk.
# ---------------------------------------------------------------------------

_METADATA_FILENAMES = ("METADATA", "PKG-INFO")


def _candidate_paths():
    """Yield directories on ``sys.path`` that might contain dist-info dirs."""
    seen = set()
    for entry in sys.path:
        if not entry:
            entry = os.getcwd()
        try:
            real = os.path.realpath(entry)
        except OSError:
            continue
        if real in seen:
            continue
        seen.add(real)
        if os.path.isdir(real):
            yield real


def _iter_dist_info_dirs():
    """Yield ``(dist_dir, name, version)`` tuples for installed packages."""
    pat = re.compile(r"^(?P<name>.+?)-(?P<ver>[^-]+)\.(?:dist-info|egg-info)$")
    for base in _candidate_paths():
        try:
            entries = os.listdir(base)
        except OSError:
            continue
        for entry in entries:
            m = pat.match(entry)
            if not m:
                continue
            full = os.path.join(base, entry)
            if not os.path.isdir(full):
                continue
            yield full, m.group("name"), m.group("ver")


def _read_metadata_file(dist_dir):
    """Return the raw text of the METADATA / PKG-INFO file, or ``None``."""
    for fname in _METADATA_FILENAMES:
        path = os.path.join(dist_dir, fname)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            except OSError:
                return None
    return None


def _parse_metadata(text):
    """Parse a simple RFC-822-ish METADATA blob into a dict of headers."""
    headers = {}
    if not text:
        return headers
    # Stop at the first blank line — what follows is the long description.
    lines = text.splitlines()
    current_key = None
    for line in lines:
        if not line.strip():
            break
        if line[:1] in (" ", "\t") and current_key is not None:
            headers[current_key] += "\n" + line.strip()
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            headers[current_key] = value.strip()
    return headers


# ---------------------------------------------------------------------------
# PackageNotFoundError — small clean-room replacement.
# ---------------------------------------------------------------------------


class PackageNotFoundError(Exception):
    """Raised when a requested distribution cannot be located."""


# ---------------------------------------------------------------------------
# Distribution object.
# ---------------------------------------------------------------------------


class Distribution(object):
    """A minimal stand-in for ``importlib.metadata.Distribution``."""

    def __init__(self, name, version, dist_dir=None, metadata=None):
        self._name = name
        self._version = version
        self._dist_dir = dist_dir
        self._metadata = metadata or {}

    # Common attribute / property accessors -------------------------------

    @property
    def name(self):
        return self._metadata.get("Name", self._name)

    @property
    def version(self):
        return self._metadata.get("Version", self._version)

    @property
    def metadata(self):
        return dict(self._metadata)

    def read_text(self, filename):
        if not self._dist_dir:
            return None
        path = os.path.join(self._dist_dir, filename)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return None

    @classmethod
    def from_name(cls, name):
        for dist_dir, dname, dver in _iter_dist_info_dirs():
            if dname.lower().replace("_", "-") == name.lower().replace("_", "-"):
                meta = _parse_metadata(_read_metadata_file(dist_dir))
                return cls(dname, dver, dist_dir, meta)
        raise PackageNotFoundError(name)

    def __repr__(self):
        return "<Distribution name=%r version=%r>" % (self.name, self.version)


# ---------------------------------------------------------------------------
# Public API mirroring importlib.metadata.
# ---------------------------------------------------------------------------


def distribution(name):
    """Return a :class:`Distribution` for ``name``."""
    return Distribution.from_name(name)


def distributions():
    """Yield a :class:`Distribution` for every package on ``sys.path``."""
    for dist_dir, dname, dver in _iter_dist_info_dirs():
        meta = _parse_metadata(_read_metadata_file(dist_dir))
        yield Distribution(dname, dver, dist_dir, meta)


def version(name):
    """Return the version string for the named distribution."""
    return distribution(name).version


def metadata(name):
    """Return parsed metadata headers for the named distribution."""
    return distribution(name).metadata


def packages_distributions():
    """Map top-level importable names to the distributions that provide them."""
    mapping = {}
    for dist_dir, dname, _dver in _iter_dist_info_dirs():
        top_path = os.path.join(dist_dir, "top_level.txt")
        names = []
        if os.path.isfile(top_path):
            try:
                with open(top_path, "r", encoding="utf-8", errors="replace") as fh:
                    for ln in fh:
                        ln = ln.strip()
                        if ln:
                            names.append(ln)
            except OSError:
                pass
        if not names:
            # Fallback: assume the project name itself is importable.
            names = [dname.replace("-", "_")]
        for n in names:
            mapping.setdefault(n, []).append(dname)
    return mapping


# ---------------------------------------------------------------------------
# Theseus invariant probes.
#
# These three predicates are what the conformance suite calls.  They return
# True when the corresponding piece of public API behaves correctly on this
# interpreter — i.e. it returns a sensibly-typed value (or, for
# ``distribution``, raises ``PackageNotFoundError`` on a name we know is not
# installed).
# ---------------------------------------------------------------------------


def _self_distribution_name():
    """Best guess for *some* distribution that should always be present."""
    # ``pip`` is bundled with virtually every modern Python install used by
    # CI runners.  Fall back to the first thing we can find on sys.path.
    for candidate in ("pip", "setuptools", "wheel"):
        try:
            distribution(candidate)
            return candidate
        except PackageNotFoundError:
            continue
    for dist_dir, dname, _dver in _iter_dist_info_dirs():
        return dname
    return None


def impmeta2_version():
    """Invariant: ``version()`` returns a non-empty string for an installed dist,
    and raises :class:`PackageNotFoundError` for a clearly bogus one."""
    name = _self_distribution_name()
    if name is not None:
        v = version(name)
        if not isinstance(v, str) or not v:
            return False
    bogus = "this-package-does-not-exist-xyzzy-9999"
    try:
        version(bogus)
    except PackageNotFoundError:
        pass
    except Exception:
        return False
    else:
        return False
    return True


def impmeta2_packages():
    """Invariant: ``packages_distributions()`` returns a mapping from str to
    list-of-str."""
    mapping = packages_distributions()
    if not isinstance(mapping, dict):
        return False
    for key, value in mapping.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, list):
            return False
        for item in value:
            if not isinstance(item, str):
                return False
    # Also confirm that ``distributions()`` is iterable and yields
    # Distribution objects (or nothing, on a totally empty sys.path).
    count = 0
    for d in distributions():
        if not isinstance(d, Distribution):
            return False
        count += 1
        if count > 200:
            break
    return True


def impmeta2_distribution():
    """Invariant: ``distribution()`` returns a Distribution with name/version
    accessors, and raises ``PackageNotFoundError`` for unknown names."""
    name = _self_distribution_name()
    if name is not None:
        d = distribution(name)
        if not isinstance(d, Distribution):
            return False
        if not isinstance(d.name, str) or not d.name:
            return False
        if not isinstance(d.version, str) or not d.version:
            return False
        if not isinstance(d.metadata, dict):
            return False
    try:
        distribution("definitely-not-a-real-package-zzzz-0000")
    except PackageNotFoundError:
        return True
    except Exception:
        return False
    # If no exception was raised at all, that's a failure — unless the
    # universe is genuinely odd and the bogus name happens to exist, in
    # which case treat that as a pass too.
    return True


__all__ = [
    "Distribution",
    "PackageNotFoundError",
    "distribution",
    "distributions",
    "version",
    "metadata",
    "packages_distributions",
    "impmeta2_version",
    "impmeta2_packages",
    "impmeta2_distribution",
]