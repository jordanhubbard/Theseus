"""
theseus_math_cr4 - Clean-room extended math utilities.
Do NOT import math. Implemented from scratch.
"""

# Constants
pi = 3.141592653589793
e = 2.718281828459045
inf = float('inf')
nan = float('nan')


def gcd(a, b):
    """Greatest common divisor using Euclidean algorithm."""
    a = abs(int(a))
    b = abs(int(b))
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """Least common multiple."""
    g = gcd(a, b)
    if g == 0:
        return 0
    return abs(int(a) * int(b)) // g


def _ln(x):
    """Natural logarithm computed via series expansion / reduction."""
    if x <= 0:
        raise ValueError("math domain error")
    if x == 1.0:
        return 0.0

    # Use the identity: ln(x) = ln(m * 2^k) = ln(m) + k*ln(2)
    # where 0.5 <= m < 1 (or 1 <= m < 2)
    # We'll reduce x to range [1, 2) and use series

    # Handle x < 1 by inverting
    if x < 1.0:
        return -_ln(1.0 / x)

    # Reduce: find k such that x = m * 2^k, 1 <= m < 2
    k = 0
    m = x
    while m >= 2.0:
        m /= 2.0
        k += 1
    while m < 1.0:
        m *= 2.0
        k -= 1

    # Now 1 <= m < 2, compute ln(m) using series ln(m) = 2*atanh((m-1)/(m+1))
    # atanh(z) = z + z^3/3 + z^5/5 + ...
    z = (m - 1.0) / (m + 1.0)
    z2 = z * z
    term = z
    result = z
    for n in range(1, 200):
        term *= z2
        contrib = term / (2 * n + 1)
        result += contrib
        if abs(contrib) < 1e-17:
            break
    ln_m = 2.0 * result

    # ln(2) computed via the same series with m=2 -> z = 1/3
    # We'll use a precomputed value for ln(2)
    ln2 = 0.6931471805599453

    return ln_m + k * ln2


def log(x, base=None):
    """Logarithm. If base is None, returns natural log."""
    if base is None:
        return _ln(x)
    if base <= 0 or base == 1:
        raise ValueError("math domain error")
    return _ln(x) / _ln(base)


def log2(x):
    """Base-2 logarithm."""
    ln2 = 0.6931471805599453
    return _ln(x) / ln2


def log10(x):
    """Base-10 logarithm."""
    ln10 = 2.302585092994046
    return _ln(x) / ln10


def sqrt(x):
    """Square root using Newton's method."""
    if x < 0:
        raise ValueError("math domain error")
    if x == 0.0:
        return 0.0
    # Initial guess
    guess = float(x)
    # Use bit-length for better initial guess
    if guess > 1.0:
        # rough estimate
        g = guess
        n = 0
        while g >= 2.0:
            g /= 4.0
            n += 1
        guess = g * (2 ** n)
        # Actually just start with x/2 or use a smarter approach
    guess = x / 2.0 if x > 1.0 else 1.0
    for _ in range(100):
        new_guess = 0.5 * (guess + x / guess)
        if abs(new_guess - guess) < 1e-15 * guess:
            break
        guess = new_guess
    return new_guess


def ceil(x):
    """Ceiling function."""
    ix = int(x)
    if x > ix:
        return ix + 1
    return ix


def floor(x):
    """Floor function."""
    ix = int(x)
    if x < ix:
        return ix - 1
    return ix


def factorial(n):
    """Factorial of non-negative integer n."""
    n = int(n)
    if n < 0:
        raise ValueError("factorial() not defined for negative values")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


# Zero-arg invariant functions
def math4_gcd():
    """Returns gcd(12, 8) == 4."""
    return gcd(12, 8)


def math4_lcm():
    """Returns lcm(4, 6) == 12."""
    return lcm(4, 6)


def math4_log2():
    """Returns log2(8) == 3.0."""
    return log2(8)