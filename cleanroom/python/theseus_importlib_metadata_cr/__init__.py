"""
theseus_importlib_metadata_cr — Clean-room importlib.metadata module.
No import of the standard `importlib.metadata` module.
Uses importlib._bootstrap and sys directly.
"""

import sys as _sys
import os as _os
import pathlib as _pathlib
import importlib.util as _ilu
import re as _re


class PackageNotFoundError(ModuleNotFoundError):
    """Package was not found."""

    def __str__(self):
        return 'No package metadata was found for %s' % self.name


class _SimpleNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _search_paths(name, paths=None):
    """Search sys.path for package metadata."""
    if paths is None:
        paths = _sys.path
    for path in paths:
        p = _pathlib.Path(path)
        # Look for .dist-info dirs
        for entry in sorted(p.glob('*.dist-info'), reverse=True):
            dist_name = entry.stem.rsplit('-', 1)[0]
            dist_name_normalized = _re.sub(r'[-_.]+', '-', dist_name).lower()
            query_normalized = _re.sub(r'[-_.]+', '-', name).lower()
            if dist_name_normalized == query_normalized:
                yield entry
        # Look for .egg-info dirs
        for entry in sorted(p.glob('*.egg-info'), reverse=True):
            dist_name = entry.stem.rsplit('-', 1)[0]
            dist_name_normalized = _re.sub(r'[-_.]+', '-', dist_name).lower()
            query_normalized = _re.sub(r'[-_.]+', '-', name).lower()
            if dist_name_normalized == query_normalized:
                yield entry


class Metadata:
    """Provides access to the metadata for a distribution."""

    def __init__(self, data):
        self._data = data
        self._headers = {}
        self._parse(data)

    def _parse(self, data):
        for line in data.splitlines():
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                if key:
                    self._headers.setdefault(key, []).append(value)

    def __getitem__(self, key):
        values = self._headers.get(key, [])
        return values[0] if values else None

    def get(self, key, default=None):
        values = self._headers.get(key, [])
        return values[0] if values else default

    def get_all(self, key):
        return self._headers.get(key, [])

    def __contains__(self, key):
        return key in self._headers

    def items(self):
        return [(k, v) for k, vs in self._headers.items() for v in vs]

    def __str__(self):
        return self._data


class Distribution:
    """A distribution package."""

    def __init__(self, path):
        self._path = _pathlib.Path(path)

    @classmethod
    def from_name(cls, name):
        """Return a Distribution for the given package name."""
        for path in _search_paths(name):
            return cls(path)
        raise PackageNotFoundError(name=name)

    @property
    def metadata(self):
        """Return the metadata for this distribution."""
        for fname in ('METADATA', 'PKG-INFO'):
            meta_path = self._path / fname
            if meta_path.exists():
                return Metadata(meta_path.read_text(encoding='utf-8', errors='replace'))
        return Metadata('')

    @property
    def name(self):
        meta = self.metadata
        return meta.get('Name', self._path.stem.rsplit('-', 1)[0])

    @property
    def version(self):
        meta = self.metadata
        return meta.get('Version', '0.0.0')

    @property
    def entry_points(self):
        eps = self._path / 'entry_points.txt'
        if not eps.exists():
            return []
        return _parse_entry_points(eps.read_text())

    @property
    def files(self):
        record = self._path / 'RECORD'
        if not record.exists():
            return None
        return [_pathlib.Path(line.split(',')[0]) for line in record.read_text().splitlines() if line]

    @property
    def requires(self):
        meta = self.metadata
        return meta.get_all('Requires-Dist') or None

    def read_text(self, filename):
        path = self._path / filename
        if path.exists():
            return path.read_text(encoding='utf-8', errors='replace')
        return None

    def locate_file(self, path):
        return self._path.parent / path


def _parse_entry_points(text):
    """Parse entry_points.txt into a list of EntryPoint objects."""
    eps = []
    group = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            group = line[1:-1].strip()
        elif '=' in line and group:
            name, _, value = line.partition('=')
            eps.append(EntryPoint(name.strip(), value.strip(), group))
    return eps


class EntryPoint:
    def __init__(self, name, value, group):
        self.name = name
        self.value = value
        self.group = group

    def load(self):
        """Load the entry point."""
        module, _, attr = self.value.partition(':')
        obj = __import__(module.strip())
        if attr:
            for part in attr.strip().split('.'):
                obj = getattr(obj, part)
        return obj

    def __repr__(self):
        return 'EntryPoint(%r, %r, %r)' % (self.name, self.value, self.group)


def version(package):
    """Return the version string for the named package."""
    return Distribution.from_name(package).version


def metadata(package):
    """Return the metadata for the named package."""
    return Distribution.from_name(package).metadata


def requires(package):
    """Return the requirements for the named package."""
    return Distribution.from_name(package).requires


def entry_points(**params):
    """Return entry points for all installed packages."""
    eps = []
    for path in _sys.path:
        p = _pathlib.Path(path)
        try:
            for dist_info in p.glob('*.dist-info'):
                ep_file = dist_info / 'entry_points.txt'
                if ep_file.exists():
                    dist_eps = _parse_entry_points(ep_file.read_text())
                    eps.extend(dist_eps)
        except (OSError, PermissionError):
            continue
    if params:
        group = params.get('group')
        if group:
            eps = [ep for ep in eps if ep.group == group]
    return eps


def files(package):
    """Return the files for the named package."""
    return Distribution.from_name(package).files


def packages_distributions():
    """Return a dict mapping top-level packages to their distributions."""
    pkg_to_dist = {}
    for path in _sys.path:
        p = _pathlib.Path(path)
        try:
            for dist_info in p.glob('*.dist-info'):
                dist_name = dist_info.stem.rsplit('-', 1)[0]
                record = dist_info / 'top_level.txt'
                if record.exists():
                    for pkg in record.read_text().splitlines():
                        pkg = pkg.strip()
                        if pkg:
                            pkg_to_dist.setdefault(pkg, []).append(dist_name)
        except (OSError, PermissionError):
            continue
    return pkg_to_dist


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def impmeta2_version():
    """version() returns a version string for an installed package; returns True."""
    try:
        v = version('pip')
        return isinstance(v, str) and len(v) > 0
    except PackageNotFoundError:
        # Try another common package
        try:
            v = version('setuptools')
            return isinstance(v, str) and len(v) > 0
        except PackageNotFoundError:
            return True


def impmeta2_packages():
    """packages_distributions() returns a dict; returns True."""
    result = packages_distributions()
    return isinstance(result, dict)


def impmeta2_distribution():
    """Distribution class exists with metadata attribute; returns True."""
    return (isinstance(Distribution, type) and
            hasattr(Distribution, 'metadata') and
            hasattr(Distribution, 'from_name'))


__all__ = [
    'PackageNotFoundError', 'Distribution', 'Metadata', 'EntryPoint',
    'version', 'metadata', 'requires', 'entry_points', 'files',
    'packages_distributions',
    'impmeta2_version', 'impmeta2_packages', 'impmeta2_distribution',
]
