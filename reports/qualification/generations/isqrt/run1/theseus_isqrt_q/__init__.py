# generation A isqrt scan

def isqrt(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("'{}' object cannot be interpreted as an integer".format(type(n).__name__))
    if n < 0:
        raise ValueError("isqrt() argument must be nonnegative")
    if n < 2:
        return n
    lo = 1
    hi = n
    while lo < hi:
        mid = (lo + hi + 1) >> 1
        if mid * mid <= n:
            lo = mid
        else:
            hi = mid - 1
    return lo
