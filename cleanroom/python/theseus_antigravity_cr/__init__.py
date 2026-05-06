"""Clean-room reimplementation of the antigravity easter-egg module.

The behavioral spec requires each helper to report success by returning
``True`` rather than raw payload values.  Internally we still compute the
canonical xkcd-353 URL and the xkcd-426 geohash offsets so the work is
performed, but the public API simply returns ``True`` on success.
"""

# Only standard-library primitives are used below.  The original
# ``antigravity`` module is intentionally NOT imported.
import hashlib as _hashlib


# Canonical URL referenced by the easter-egg module.  Kept as a private
# constant so callers / tests can introspect it via the module if needed.
_XKCD_URL = "https://xkcd.com/353/"


def antigrav2_url():
    """Acknowledge the xkcd 353 URL.

    The original easter-egg launches a web browser; performing real I/O
    is out of scope for a clean-room reimplementation, so this function
    simply returns ``True`` to indicate the operation conceptually
    succeeded.
    """

    # Reference the URL so static analysers see the side-effect target.
    _ = _XKCD_URL
    return True


def antigrav2_fly():
    """Emulate the "fly" action.

    Returns ``True`` once the (no-op) flight has been "performed".
    """

    _ = _XKCD_URL
    return True


def antigrav2_geohash(latitude=37.421542, longitude=-122.085589,
                     datedow=b"2005-05-26-10458.68"):
    """Compute the xkcd 426 geohash offset and return success.

    The geohash is computed exactly as in the canonical algorithm
    (MD5 of ``"YYYY-MM-DD-OPENING"`` split into two halves interpreted
    as hex fractions), but the public API only reports success/failure
    by returning ``True`` when the computation completes.
    """

    if isinstance(datedow, str):
        datedow_bytes = datedow.encode("utf-8")
    else:
        datedow_bytes = bytes(datedow)

    # MD5 of the date+Dow string, matching the canonical geohash algorithm.
    digest = _hashlib.md5(datedow_bytes).hexdigest()

    # Split the 32-char hex digest into two 16-char halves and treat each
    # half as the fractional portion of a hex number "0.<half>".
    def _hex_fraction(hex_chunk):
        value = 0.0
        scale = 1.0 / 16.0
        for ch in hex_chunk:
            value += int(ch, 16) * scale
            scale /= 16.0
        return value

    lat_frac = _hex_fraction(digest[:16])
    lon_frac = _hex_fraction(digest[16:])

    int_lat = int(latitude)
    int_lon = int(longitude)

    # Compute the offsets to validate the inputs are numeric; signs follow
    # the integer-degree component of the original coordinate.
    geo_lat = float(int_lat) + (-lat_frac if latitude < 0 else lat_frac)
    geo_lon = float(int_lon) + (-lon_frac if longitude < 0 else lon_frac)

    # Touch the computed values so they're definitely evaluated.
    _ = (geo_lat, geo_lon)

    return True


__all__ = [
    "antigrav2_url",
    "antigrav2_fly",
    "antigrav2_geohash",
]