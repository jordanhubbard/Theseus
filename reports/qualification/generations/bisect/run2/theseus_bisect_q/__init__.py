# generation B index loop
"""Clean-room array bisection helpers."""


def bisect_left(a, x, lo=0, hi=None):
    """Return the leftmost insertion index for x in sorted sequence a."""
    if lo < 0:
        raise ValueError("lo must be non-negative")
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def bisect_right(a, x, lo=0, hi=None):
    """Return the rightmost insertion index for x in sorted sequence a."""
    if lo < 0:
        raise ValueError("lo must be non-negative")
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if x < a[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


bisect = bisect_right


def insort_left(a, x, lo=0, hi=None):
    """Insert x before existing equal values in sorted list a."""
    a.insert(bisect_left(a, x, lo, hi), x)


def insort_right(a, x, lo=0, hi=None):
    """Insert x after existing equal values in sorted list a."""
    a.insert(bisect_right(a, x, lo, hi), x)


insort = insort_right


__all__ = [
    "bisect_left",
    "bisect_right",
    "bisect",
    "insort_left",
    "insort_right",
    "insort",
]
