"""Clean-room implementation of bisect module functionality.

Implements binary search and insertion algorithms without importing the
original `bisect` module.
"""


def bisect_left(a, x, lo=0, hi=None, *, key=None):
    """Return the leftmost insertion point for x in sorted sequence a.

    All values in a[lo:i] are < x (or key(...) < x), all values in a[i:hi]
    are >= x (or key(...) >= x).
    """
    if lo < 0:
        raise ValueError("lo must be non-negative")
    if hi is None:
        hi = len(a)
    if key is None:
        while lo < hi:
            mid = (lo + hi) // 2
            if a[mid] < x:
                lo = mid + 1
            else:
                hi = mid
    else:
        while lo < hi:
            mid = (lo + hi) // 2
            if key(a[mid]) < x:
                lo = mid + 1
            else:
                hi = mid
    return lo


def bisect_right(a, x, lo=0, hi=None, *, key=None):
    """Return the rightmost insertion point for x in sorted sequence a.

    All values in a[lo:i] are <= x (or key(...) <= x), all values in a[i:hi]
    are > x (or key(...) > x).
    """
    if lo < 0:
        raise ValueError("lo must be non-negative")
    if hi is None:
        hi = len(a)
    if key is None:
        while lo < hi:
            mid = (lo + hi) // 2
            if x < a[mid]:
                hi = mid
            else:
                lo = mid + 1
    else:
        while lo < hi:
            mid = (lo + hi) // 2
            if x < key(a[mid]):
                hi = mid
            else:
                lo = mid + 1
    return lo


# Aliases matching the standard library names.
bisect = bisect_right


def insort_left(a, x, lo=0, hi=None, *, key=None):
    """Insert x into sorted sequence a at leftmost position keeping it sorted."""
    if key is None:
        i = bisect_left(a, x, lo, hi)
        a.insert(i, x)
    else:
        i = bisect_left(a, key(x), lo, hi, key=key)
        a.insert(i, x)


def insort_right(a, x, lo=0, hi=None, *, key=None):
    """Insert x into sorted sequence a at rightmost position keeping it sorted."""
    if key is None:
        i = bisect_right(a, x, lo, hi)
        a.insert(i, x)
    else:
        i = bisect_right(a, key(x), lo, hi, key=key)
        a.insert(i, x)


# Default insort matches insort_right (same as the standard library).
insort = insort_right


# ---------------------------------------------------------------------------
# Invariant probe functions.  These exercise the public API and return the
# values the verifier expects.
# ---------------------------------------------------------------------------

def bisect2_insort():
    """Verify insort keeps a list sorted and returns True on success."""
    data = [1, 3, 5, 7]
    insort(data, 4)
    expected = [1, 3, 4, 5, 7]
    if data != expected:
        return False
    # Also exercise insort_left to make sure both work.
    data2 = [1, 2, 2, 3]
    insort_left(data2, 2)
    if data2 != [1, 2, 2, 2, 3]:
        return False
    return True


def bisect2_left():
    """Return bisect_left([1, 2, 3, 4, 5], 3) which is 2."""
    return bisect_left([1, 2, 3, 4, 5], 3)


def bisect2_right():
    """Return bisect_right([1, 2, 3, 4, 5], 3) which is 3."""
    return bisect_right([1, 2, 3, 4, 5], 3)


__all__ = [
    "bisect",
    "bisect_left",
    "bisect_right",
    "insort",
    "insort_left",
    "insort_right",
    "bisect2_insort",
    "bisect2_left",
    "bisect2_right",
]