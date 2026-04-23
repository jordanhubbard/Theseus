"""
theseus_antigravity_cr — Clean-room antigravity module.
No import of the standard `antigravity` module.
"""

import webbrowser as _wb
import math as _math


XKCD_URL = 'https://xkcd.com/353/'


def fly():
    """Open the xkcd Python comic in a web browser."""
    _wb.open(XKCD_URL)


def geohash(latitude, longitude, datedow):
    """
    Compute a Geohash given a date and Dow Jones opening value.
    latitude and longitude are floats.
    datedow is a bytes-like date+dow string e.g. b'2005-05-2610800.00'.
    Returns (latitude, longitude) of computed hash point.
    """
    import hashlib as _hl
    import struct as _st
    h = _hl.md5(datedow).hexdigest()
    p, q = [('%f' % _st.unpack('>I', bytes.fromhex(h[i:i+8]))[0]) for i in (0, 8)]
    e = float('0.' + p.split('.')[1]) + int(latitude)
    n = float('0.' + q.split('.')[1]) + int(longitude)
    return round(e, 6), round(n, 6)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def antigrav2_url():
    """antigravity module exposes a URL constant; returns True."""
    return (isinstance(XKCD_URL, str) and
            'xkcd' in XKCD_URL and
            XKCD_URL.startswith('https://'))


def antigrav2_fly():
    """fly() function exists and is callable; returns True."""
    return callable(fly)


def antigrav2_geohash():
    """geohash() function exists and accepts args; returns True."""
    result = geohash(37, -122, b'2005-05-2610800.00')
    return (isinstance(result, tuple) and
            len(result) == 2 and
            all(isinstance(x, float) for x in result))


__all__ = [
    'XKCD_URL', 'fly', 'geohash',
    'antigrav2_url', 'antigrav2_fly', 'antigrav2_geohash',
]
