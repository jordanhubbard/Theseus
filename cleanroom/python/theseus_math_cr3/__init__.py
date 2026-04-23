# theseus_math_cr3 - Clean-room extended math functions
# Do NOT import math or any third-party library

def isnan(x):
    """True if x is NaN (Not a Number)."""
    return x != x

def isinf(x):
    """True if x is infinite (positive or negative infinity)."""
    return x == float('inf') or x == float('-inf')

def isfinite(x):
    """True if x is neither inf nor nan."""
    return not (x != x or x == float('inf') or x == float('-inf'))

def prod(iterable, start=1):
    """Return the product of all elements in iterable, starting from start."""
    result = start
    for item in iterable:
        result *= item
    return result

def perm(n, k=None):
    """
    Number of permutations of n items taken k at a time.
    perm(n) = n!
    perm(n, k) = n! / (n-k)!
    """
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative integer")
    if k is None:
        k = n
    if not isinstance(k, int) or k < 0:
        raise ValueError("k must be a non-negative integer")
    if k > n:
        return 0
    result = 1
    for i in range(n, n - k, -1):
        result *= i
    return result

def comb(n, k):
    """
    Number of combinations (n choose k).
    comb(n, k) = n! / (k! * (n-k)!)
    """
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative integer")
    if not isinstance(k, int) or k < 0:
        raise ValueError("k must be a non-negative integer")
    if k > n:
        return 0
    # Optimize by using the smaller of k and n-k
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result

# Invariant test functions - return the actual computed value, not a boolean
def math3_isfinite():
    """isfinite(1.0) == True"""
    return isfinite(1.0)

def math3_prod():
    """prod([2, 3, 4]) == 24"""
    return prod([2, 3, 4])

def math3_comb():
    """comb(5, 2) == 10"""
    return comb(5, 2)