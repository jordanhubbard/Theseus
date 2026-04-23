"""
theseus_math_cr5 — Clean-room extended math utilities.
No import of math or any third-party library.
"""


def _factorial(n):
    """Compute n! for non-negative integer n."""
    if not isinstance(n, int) or n < 0:
        raise ValueError(f"factorial requires a non-negative integer, got {n!r}")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def comb(n, k):
    """
    Binomial coefficient: number of ways to choose k items from n without repetition.
    comb(n, k) = n! / (k! * (n-k)!) for 0 <= k <= n.
    Returns 0 if k < 0 or k > n.
    """
    if not isinstance(n, int) or not isinstance(k, int):
        raise TypeError("comb() requires integer arguments")
    if n < 0:
        raise ValueError("comb() requires n >= 0")
    if k < 0 or k > n:
        return 0
    # Optimise by using the smaller of k and n-k
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def perm(n, k=None):
    """
    Number of k-permutations of n.
    perm(n, k) = n! / (n-k)! for 0 <= k <= n.
    If k is None, returns n! (all permutations).
    """
    if not isinstance(n, int):
        raise TypeError("perm() requires integer arguments")
    if n < 0:
        raise ValueError("perm() requires n >= 0")
    if k is None:
        return _factorial(n)
    if not isinstance(k, int):
        raise TypeError("perm() requires integer arguments")
    if k < 0 or k > n:
        return 0
    result = 1
    for i in range(n, n - k, -1):
        result *= i
    return result


def isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
    """
    Return True if a and b are close to each other.
    abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
    """
    if rel_tol < 0 or abs_tol < 0:
        raise ValueError("tolerances must be non-negative")
    if a == b:
        return True
    diff = abs(a - b)
    return diff <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def prod(iterable, start=1):
    """
    Return the product of all elements in iterable, starting with start.
    """
    result = start
    for x in iterable:
        result *= x
    return result


def dist(p, q):
    """
    Return the Euclidean distance between two points p and q
    given as sequences of coordinates.
    """
    if len(p) != len(q):
        raise ValueError("dist() requires both points to have the same number of dimensions")
    sum_sq = 0.0
    for a, b in zip(p, q):
        diff = a - b
        sum_sq += diff * diff
    # Integer square root approximation using Newton's method for floats
    return _sqrt(sum_sq)


def _sqrt(x):
    """Compute square root of x using Newton's method."""
    if x < 0:
        raise ValueError("math domain error: sqrt of negative number")
    if x == 0:
        return 0.0
    # Initial guess
    guess = float(x)
    # Use a reasonable starting point
    # Rough estimate: find magnitude
    g = 1.0
    while g * g < x:
        g *= 2.0
    while g * g > x:
        g /= 2.0
    # Newton-Raphson iterations
    for _ in range(100):
        new_g = (g + x / g) / 2.0
        if abs(new_g - g) < 1e-15 * new_g:
            break
        g = new_g
    return new_g


# ---------------------------------------------------------------------------
# Zero-argument invariant helpers
# ---------------------------------------------------------------------------

def math5_comb():
    """Return comb(5, 2) == 10."""
    return comb(5, 2)


def math5_perm():
    """Return perm(5, 2) == 20."""
    return perm(5, 2)


def math5_isclose():
    """Return isclose(0.1 + 0.2, 0.3) within default tolerance."""
    return isclose(0.1 + 0.2, 0.3)