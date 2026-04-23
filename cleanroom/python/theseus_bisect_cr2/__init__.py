"""
theseus_bisect_cr2 - Clean-room implementation of bisect utilities.
"""


def bisect_left(a, x, lo=0, hi=None):
    """
    Find the leftmost position in sorted list `a` where `x` can be inserted
    to keep `a` sorted.
    """
    if lo < 0:
        raise ValueError('lo must be non-negative')
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
    """
    Find the rightmost position in sorted list `a` where `x` can be inserted
    to keep `a` sorted.
    """
    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if x < a[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


def bisect(a, x, lo=0, hi=None):
    """
    Same as bisect_right. Find the rightmost insertion point for `x` in `a`.
    """
    return bisect_right(a, x, lo=lo, hi=hi)


def insort_left(a, x, lo=0, hi=None):
    """
    Insert `x` into sorted list `a` at the leftmost position that keeps `a` sorted.
    """
    pos = bisect_left(a, x, lo=lo, hi=hi)
    a.insert(pos, x)


def insort_right(a, x, lo=0, hi=None):
    """
    Insert `x` into sorted list `a` at the rightmost position that keeps `a` sorted.
    """
    pos = bisect_right(a, x, lo=lo, hi=hi)
    a.insert(pos, x)


def insort(a, x, lo=0, hi=None):
    """
    Same as insort_right. Insert `x` into sorted list `a`.
    """
    insort_right(a, x, lo=lo, hi=hi)


# ---------------------------------------------------------------------------
# Zero-arg invariant functions
# ---------------------------------------------------------------------------

def bisect2_insort():
    """
    Invariant: a=[1,3,5]; insort(a, 4); a == [1,3,4,5]
    Returns [1, 3, 4, 5]
    """
    a = [1, 3, 5]
    insort(a, 4)
    return a


def bisect2_insort_left():
    """
    Invariant: a=[1,3,3,5]; insort_left(a, 3); a[1] == 3
    Returns 3
    """
    a = [1, 3, 3, 5]
    insort_left(a, 3)
    return a[1]


def bisect2_insort_right():
    """
    Invariant: a=[1,2]; insort_right(a, 2); a[-1] == 2
    Returns 2
    """
    a = [1, 2]
    insort_right(a, 2)
    return a[-1]