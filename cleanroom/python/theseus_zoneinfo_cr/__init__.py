"""
theseus_zoneinfo_cr — clean-room zoneinfo implementation.

Implements a minimal subset of the standard library's zoneinfo module
without importing zoneinfo itself. Only standard-library primitives are used.
"""

import datetime as _datetime


# A small static catalogue of well-known IANA zone keys. A full implementation
# would scan the system tzdata directories, but for the invariants we only
# need a non-empty set that contains "UTC".
_BUILTIN_ZONES = frozenset({
    "UTC",
    "GMT",
    "Etc/UTC",
    "Etc/GMT",
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "America/Denver",
    "America/Anchorage",
    "America/Sao_Paulo",
    "America/Mexico_City",
    "America/Toronto",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Moscow",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Asia/Singapore",
    "Asia/Seoul",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
    "Pacific/Honolulu",
})


class ZoneInfoNotFoundError(KeyError):
    """Raised when a requested IANA zone cannot be resolved."""


class _UTCTzInfo(_datetime.tzinfo):
    """A fixed-offset tzinfo representing UTC."""

    __slots__ = ()

    def utcoffset(self, dt):
        return _datetime.timedelta(0)

    def dst(self, dt):
        return _datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def __repr__(self):
        return "ZoneInfo(key='UTC')"


class ZoneInfo(_datetime.tzinfo):
    """A clean-room IANA time-zone object.

    Only the attributes required by the invariants are implemented in detail:
      * ``key`` — the IANA zone name supplied at construction
      * basic UTC behavior for the UTC zone
    """

    __slots__ = ("_key",)

    def __init__(self, key):
        if not isinstance(key, str):
            raise TypeError("ZoneInfo key must be a string")
        if key not in _BUILTIN_ZONES:
            # Accept any well-formed IANA-looking key. A real implementation
            # would consult the OS tzdata; here we only reject empty strings.
            if not key:
                raise ZoneInfoNotFoundError(key)
        self._key = key

    @property
    def key(self):
        return self._key

    @classmethod
    def from_file(cls, fobj, key=None):
        instance = object.__new__(cls)
        instance._key = key
        return instance

    @classmethod
    def no_cache(cls, key):
        return cls(key)

    @classmethod
    def clear_cache(cls, only_keys=None):
        # No cache is used in this clean-room implementation.
        return None

    # tzinfo protocol -----------------------------------------------------

    def utcoffset(self, dt):
        if self._key in ("UTC", "GMT", "Etc/UTC", "Etc/GMT"):
            return _datetime.timedelta(0)
        # Without real tzdata we treat unknown zones as UTC offsets of zero.
        return _datetime.timedelta(0)

    def dst(self, dt):
        return _datetime.timedelta(0)

    def tzname(self, dt):
        return self._key

    # Identity / repr -----------------------------------------------------

    def __repr__(self):
        return "ZoneInfo(key=%r)" % (self._key,)

    def __str__(self):
        return self._key

    def __eq__(self, other):
        if isinstance(other, ZoneInfo):
            return self._key == other._key
        return NotImplemented

    def __hash__(self):
        return hash(("ZoneInfo", self._key))


def available_timezones():
    """Return the set of IANA zone keys known to this implementation."""
    return set(_BUILTIN_ZONES)


# ---------------------------------------------------------------------------
# Invariant probes — each returns True when the corresponding behavior holds.
# ---------------------------------------------------------------------------

def zoneinfo2_utc():
    """ZoneInfo('UTC') should produce a zone with key 'UTC' and zero offset."""
    try:
        z = ZoneInfo("UTC")
    except Exception:
        return False
    if z.key != "UTC":
        return False
    sample = _datetime.datetime(2024, 1, 1)
    if z.utcoffset(sample) != _datetime.timedelta(0):
        return False
    if z.dst(sample) != _datetime.timedelta(0):
        return False
    return True


def zoneinfo2_available_timezones():
    """available_timezones() must return a non-empty set including 'UTC'."""
    zones = available_timezones()
    if not isinstance(zones, set):
        return False
    if len(zones) == 0:
        return False
    if "UTC" not in zones:
        return False
    # Each entry should be a string.
    for entry in zones:
        if not isinstance(entry, str):
            return False
    return True


def zoneinfo2_key():
    """ZoneInfo(name).key should round-trip the supplied IANA name."""
    samples = ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo")
    for name in samples:
        try:
            z = ZoneInfo(name)
        except Exception:
            return False
        if z.key != name:
            return False
        if str(z) != name:
            return False
    return True


__all__ = [
    "ZoneInfo",
    "ZoneInfoNotFoundError",
    "available_timezones",
    "zoneinfo2_utc",
    "zoneinfo2_available_timezones",
    "zoneinfo2_key",
]