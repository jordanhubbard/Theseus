def bisect_left(a, x, lo=0, hi=None):
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
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def insort_left(a, x, lo=0, hi=None):
    pos = bisect_left(a, x, lo, hi if hi is not None else len(a))
    a.insert(pos, x)


def insort_right(a, x, lo=0, hi=None):
    pos = bisect_right(a, x, lo, hi if hi is not None else len(a))
    a.insert(pos, x)


# Invariant test functions
def bisect_left_result():
    return bisect_left([1, 2, 3, 4, 5], 3)


def bisect_right_result():
    return bisect_right([1, 2, 3, 3, 5], 3)


def bisect_insort_result():
    a = [1, 4, 5]
    insort_left(a, 3)
    return a