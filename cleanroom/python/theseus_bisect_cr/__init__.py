"""
theseus_bisect_cr — Clean-room bisect module.
No import of the standard `bisect` module.
"""


def bisect_left(a, x, lo=0, hi=None, *, key=None):
    """Return leftmost index where x can be inserted into sorted a."""
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
    """Return rightmost index where x can be inserted into sorted a."""
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


bisect = bisect_right


def insort_left(a, x, lo=0, hi=None, *, key=None):
    """Insert x into sorted list a, keeping it sorted (leftmost position)."""
    if key is None:
        idx = bisect_left(a, x, lo, hi)
    else:
        idx = bisect_left(a, key(x), lo, hi, key=key)
    a.insert(idx, x)


def insort_right(a, x, lo=0, hi=None, *, key=None):
    """Insert x into sorted list a, keeping it sorted (rightmost position)."""
    if key is None:
        idx = bisect_right(a, x, lo, hi)
    else:
        idx = bisect_right(a, key(x), lo, hi, key=key)
    a.insert(idx, x)


insort = insort_right


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def bisect2_insort():
    """insort keeps list sorted after insertion; returns True."""
    a = [1, 3, 5, 7]
    insort(a, 4)
    return a == [1, 3, 4, 5, 7]


def bisect2_left():
    """bisect_left([1,2,3,4], 3) returns 2; returns 2."""
    return bisect_left([1, 2, 3, 4], 3)


def bisect2_right():
    """bisect_right([1,2,3,4], 3) returns 3; returns 3."""
    return bisect_right([1, 2, 3, 4], 3)


__all__ = [
    'bisect_left', 'bisect_right', 'bisect',
    'insort_left', 'insort_right', 'insort',
    'bisect2_insort', 'bisect2_left', 'bisect2_right',
]
