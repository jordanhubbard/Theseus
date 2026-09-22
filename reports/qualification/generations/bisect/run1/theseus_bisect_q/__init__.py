# generation A binary search

__all__ = [
    "bisect_left",
    "bisect_right",
    "bisect",
    "insort_left",
    "insort_right",
    "insort",
]


def bisect_left(a, x, lo=0, hi=None):
    """Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e < x, and all e in
    a[i:] have e >= x.  So if x already appears in the list, a.insert(i, x) will
    insert just before the leftmost x already there.
    """
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
    """Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e <= x, and all e in
    a[i:] have e > x.  So if x already appears in the list, a.insert(i, x) will
    insert just after the rightmost x already there.
    """
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo


bisect = bisect_right


def insort_left(a, x, lo=0, hi=None):
    """Insert item x in list a, assuming a is sorted.

    If x is already in a, insert it to the left of the leftmost x.
    """
    lo = bisect_left(a, x, lo, hi)
    a.insert(lo, x)


def insort_right(a, x, lo=0, hi=None):
    """Insert item x in list a, assuming a is sorted.

    If x is already in a, insert it to the right of the rightmost x.
    """
    lo = bisect_right(a, x, lo, hi)
    a.insert(lo, x)


insort = insort_right
