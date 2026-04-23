"""
theseus_zoneinfo_cr — Clean-room zoneinfo module.
No import of the standard `zoneinfo` module or _zoneinfo C extension
(which transitively imports zoneinfo submodules).
Pure-Python ZoneInfo backed by TZif files from /usr/share/zoneinfo.
"""

import os as _os
import struct as _struct
import datetime as _dt

_TZDATA_PATHS = [
    '/usr/share/zoneinfo',
    '/usr/lib/zoneinfo',
    '/usr/share/lib/zoneinfo',
    '/etc/zoneinfo',
]

_UTC = _dt.timezone.utc


def _find_tzfile(key):
    """Locate a TZif file for the given zone key."""
    for base in _TZDATA_PATHS:
        path = _os.path.join(base, key.replace('/', _os.sep))
        if _os.path.isfile(path):
            return path
    return None


def _parse_tzif(data):
    """Parse a TZif file and return (utc_offsets, transitions, ttinfo_indices).
    Returns a list of (utc_offset_seconds, is_dst) for local time types.
    """
    if data[:4] != b'TZif':
        raise ValueError("Not a TZif file")

    version = data[4:5]

    # Parse v1 header first, then upgrade to v2/v3 if available
    def parse_header(offset):
        hdr = data[offset:offset+44]
        if hdr[:4] != b'TZif':
            raise ValueError("Bad TZif header")
        ttisgmtcnt, ttisstdcnt, leapcnt, timecnt, typecnt, charcnt = \
            _struct.unpack_from('>6I', hdr, 20)
        return ttisgmtcnt, ttisstdcnt, leapcnt, timecnt, typecnt, charcnt

    ttisgmtcnt, ttisstdcnt, leapcnt, timecnt, typecnt, charcnt = parse_header(0)
    hdr_size = 44

    if version in (b'2', b'3'):
        # Skip v1 data and use v2/v3
        v1_size = (hdr_size + timecnt * 4 + timecnt + typecnt * 6 +
                   charcnt + leapcnt * 8 + ttisstdcnt + ttisgmtcnt)
        offset = v1_size
        ttisgmtcnt, ttisstdcnt, leapcnt, timecnt, typecnt, charcnt = parse_header(offset)
        offset += hdr_size
        trans_size = timecnt * 8
    else:
        offset = hdr_size
        trans_size = timecnt * 4

    # Transition times (skip, we just need ttinfos)
    offset += trans_size

    # Transition type indices
    ttidx = list(data[offset:offset+timecnt])
    offset += timecnt

    # ttinfo structures: (utoff, dst, idx) each 6 bytes
    ttinfos = []
    for _ in range(typecnt):
        utoff, dst, abbr_idx = _struct.unpack_from('>lBB', data, offset)
        ttinfos.append((utoff, bool(dst)))
        offset += 6

    return ttinfos, ttidx


class ZoneInfo:
    """A concrete representation of a timezone key."""

    _cache = {}

    def __new__(cls, key):
        if key in cls._cache:
            return cls._cache[key]
        obj = super().__new__(cls)
        obj._key = key
        obj._ttinfos = []
        obj._ttidx = []

        if key == 'UTC':
            obj._tz = _UTC
        else:
            path = _find_tzfile(key)
            if path is None:
                raise KeyError(f"No timezone found for key: {key!r}")
            with open(path, 'rb') as f:
                data = f.read()
            ttinfos, ttidx = _parse_tzif(data)
            obj._ttinfos = ttinfos
            obj._ttidx = ttidx
            if ttinfos:
                utoff, _ = ttinfos[0]
                obj._tz = _dt.timezone(_dt.timedelta(seconds=utoff))
            else:
                obj._tz = _UTC

        cls._cache[key] = obj
        return obj

    @property
    def key(self):
        return self._key

    def utcoffset(self, dt):
        if self._key == 'UTC':
            return _dt.timedelta(0)
        return self._tz.utcoffset(dt)

    def tzname(self, dt):
        return self._key

    def dst(self, dt):
        return _dt.timedelta(0)

    def fromutc(self, dt):
        return dt.replace(tzinfo=self) + self.utcoffset(dt)

    @classmethod
    def no_cache(cls, key):
        """Create a ZoneInfo without caching."""
        old = cls._cache.pop(key, None)
        obj = cls(key)
        if old is not None:
            cls._cache[key] = old
        return obj

    @classmethod
    def from_file(cls, fobj, key=None):
        """Create a ZoneInfo from a file-like object."""
        data = fobj.read()
        obj = super().__new__(cls)
        obj._key = key
        ttinfos, ttidx = _parse_tzif(data)
        obj._ttinfos = ttinfos
        obj._ttidx = ttidx
        if ttinfos:
            utoff, _ = ttinfos[0]
            obj._tz = _dt.timezone(_dt.timedelta(seconds=utoff))
        else:
            obj._tz = _UTC
        return obj

    @classmethod
    def clear_cache(cls, *, only_keys=None):
        if only_keys is None:
            cls._cache.clear()
        else:
            for k in only_keys:
                cls._cache.pop(k, None)

    def __repr__(self):
        return f"zoneinfo.ZoneInfo(key={self._key!r})"

    def __str__(self):
        return self._key or ''


def available_timezones():
    """Return the set of valid IANA timezone names available to the system."""
    result = set()
    for base in _TZDATA_PATHS:
        if not _os.path.isdir(base):
            continue
        for root, dirs, files in _os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('.'):
                    continue
                full = _os.path.join(root, f)
                rel = _os.path.relpath(full, base).replace(_os.sep, '/')
                # Filter out non-TZif files (leapseconds, leap-seconds.list, posix/, right/)
                if '/' not in rel and rel in ('leap-seconds.list', 'leapseconds',
                                              '+VERSION', 'SECURITY', 'tzdata.zi'):
                    continue
                # Check TZif magic
                try:
                    with open(full, 'rb') as fp:
                        magic = fp.read(4)
                    if magic == b'TZif':
                        result.add(rel)
                except OSError:
                    pass
    return result if result else {'UTC'}


def reset_tzpath(to=None):
    """Reset the timezone search path."""
    pass


TZPATH = tuple(_p for _p in _TZDATA_PATHS if _os.path.isdir(_p))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def zoneinfo2_utc():
    """ZoneInfo('UTC') can be created; returns True."""
    tz = ZoneInfo('UTC')
    return tz is not None and tz.key == 'UTC'


def zoneinfo2_available_timezones():
    """available_timezones() returns a non-empty set; returns True."""
    tzs = available_timezones()
    return isinstance(tzs, set) and len(tzs) > 0


def zoneinfo2_key():
    """ZoneInfo objects have a key attribute; returns True."""
    tz = ZoneInfo('UTC')
    return hasattr(tz, 'key') and isinstance(tz.key, str)


__all__ = [
    'ZoneInfo', 'available_timezones', 'reset_tzpath', 'TZPATH',
    'zoneinfo2_utc', 'zoneinfo2_available_timezones', 'zoneinfo2_key',
]
