"""
theseus_math_cr2: Clean-room extended math functions.
Implements log, log2, log10, sin, cos, tan, atan2, pi, e from scratch.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# pi computed via Machin-like formula: pi = 16*arctan(1/5) - 4*arctan(1/239)
# Using the Gregory-Leibniz / Machin formula with high precision via fractions

def _arctan_series(x, terms=100):
    """Compute arctan(x) via Taylor series: sum_{k=0}^{inf} (-1)^k * x^(2k+1)/(2k+1)
    Converges well for |x| <= 1."""
    result = 0.0
    x_pow = x
    x2 = x * x
    for k in range(terms):
        term = x_pow / (2 * k + 1)
        if k % 2 == 0:
            result += term
        else:
            result -= term
        x_pow *= x2
        if abs(x_pow / (2 * k + 3)) < 1e-18:
            break
    return result


def _compute_pi():
    # Machin's formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    return 16.0 * _arctan_series(1.0 / 5.0, 200) - 4.0 * _arctan_series(1.0 / 239.0, 200)


pi = _compute_pi()


def _compute_e():
    """Compute e via Taylor series: e = sum_{n=0}^{inf} 1/n!"""
    result = 0.0
    term = 1.0
    for n in range(1, 100):
        result += term
        term /= n
        if term < 1e-18:
            break
    return result


e = _compute_e()


# ---------------------------------------------------------------------------
# Natural logarithm
# ---------------------------------------------------------------------------

def _ln(x):
    """Compute natural logarithm of x > 0."""
    if x <= 0:
        raise ValueError("math domain error: log requires x > 0")
    if x == 1.0:
        return 0.0

    # Use identity: ln(x) = ln(m * 2^k) = k*ln(2) + ln(m)
    # where 0.5 <= m < 1 (or 1 <= m < 2)
    # We'll reduce x to range [1, 2) and use series

    # First, handle x by extracting power of 2
    # Find k such that 2^k <= x < 2^(k+1), i.e., 1 <= x/2^k < 2
    k = 0
    y = x
    if y >= 2.0:
        while y >= 2.0:
            y /= 2.0
            k += 1
    elif y < 1.0:
        while y < 1.0:
            y *= 2.0
            k -= 1

    # Now 1 <= y < 2, compute ln(y) using series
    # ln(y) = 2 * arctanh((y-1)/(y+1))
    # arctanh(z) = z + z^3/3 + z^5/5 + ... for |z| < 1
    z = (y - 1.0) / (y + 1.0)
    z2 = z * z
    result = 0.0
    z_pow = z
    for n in range(200):
        term = z_pow / (2 * n + 1)
        result += term
        z_pow *= z2
        if abs(z_pow / (2 * n + 3)) < 1e-18:
            break
    ln_y = 2.0 * result

    # ln(2) computed similarly but we need it bootstrapped
    # We'll compute ln(2) inline using the same method with y=2 reduced
    # Actually we already have y in [1,2), so ln(2) is needed for the k term
    # Compute ln(2) using arctanh series with z = (2-1)/(2+1) = 1/3
    ln2 = _ln2_const()

    return k * ln2 + ln_y


def _ln2_const():
    """Compute ln(2) = 2 * arctanh(1/3)"""
    z = 1.0 / 3.0
    z2 = z * z
    result = 0.0
    z_pow = z
    for n in range(200):
        term = z_pow / (2 * n + 1)
        result += term
        z_pow *= z2
        if abs(z_pow / (2 * n + 3)) < 1e-18:
            break
    return 2.0 * result


# Cache ln(2) and ln(10) for efficiency
_LN2 = _ln2_const()
_LN10 = None  # will be computed after _ln is defined


def _get_ln10():
    global _LN10
    if _LN10 is None:
        _LN10 = _ln(10.0)
    return _LN10


# ---------------------------------------------------------------------------
# Public log functions
# ---------------------------------------------------------------------------

def log(x, base=None):
    """
    Natural logarithm of x, or logarithm of x to the given base.
    log(x) = ln(x)
    log(x, base) = ln(x) / ln(base)
    """
    ln_x = _ln(x)
    if base is None:
        return ln_x
    if base <= 0 or base == 1:
        raise ValueError("math domain error: invalid base")
    return ln_x / _ln(base)


def log2(x):
    """Base-2 logarithm of x."""
    return _ln(x) / _LN2


def log10(x):
    """Base-10 logarithm of x."""
    return _ln(x) / _get_ln10()


# ---------------------------------------------------------------------------
# Trigonometric functions
# ---------------------------------------------------------------------------

def _reduce_angle(x):
    """Reduce x to [-pi, pi] range."""
    # x mod 2*pi
    two_pi = 2.0 * pi
    x = x - two_pi * int(x / two_pi)
    if x > pi:
        x -= two_pi
    elif x < -pi:
        x += two_pi
    return x


def sin(x):
    """Sine of x (in radians)."""
    # Reduce to [-pi, pi]
    x = _reduce_angle(x)

    # Further reduce to [-pi/2, pi/2] using symmetry
    # sin(pi - x) = sin(x), sin(-x) = -sin(x)
    if x > pi / 2.0:
        x = pi - x
    elif x < -pi / 2.0:
        x = -pi - x

    # Taylor series: sin(x) = x - x^3/3! + x^5/5! - ...
    result = 0.0
    term = x
    x2 = x * x
    for n in range(1, 50):
        result += term
        term *= -x2 / ((2 * n) * (2 * n + 1))
        if abs(term) < 1e-18:
            break
    return result


def cos(x):
    """Cosine of x (in radians)."""
    # cos(x) = sin(x + pi/2)
    return sin(x + pi / 2.0)


def tan(x):
    """Tangent of x (in radians)."""
    c = cos(x)
    if c == 0.0:
        raise ValueError("math domain error: tan undefined at this point")
    return sin(x) / c


# ---------------------------------------------------------------------------
# atan2
# ---------------------------------------------------------------------------

def _atan(x):
    """Compute arctan(x) for any real x."""
    if x < 0:
        return -_atan(-x)
    if x > 1.0:
        # arctan(x) = pi/2 - arctan(1/x)
        return pi / 2.0 - _atan(1.0 / x)
    if x > 0.5:
        # Use identity: arctan(x) = arctan(c) + arctan((x-c)/(1+x*c))
        # with c = sqrt(3)/3 (i.e., arctan(c) = pi/6)
        # Or simpler: reduce using arctan(x) = 2*arctan(x/(1+sqrt(1+x^2)))
        # Use: arctan(x) = pi/4 - arctan((1-x)/(1+x)) for x near 1
        z = (x - 1.0) / (1.0 + x)
        return pi / 4.0 + _arctan_series(z, 200)
    # For |x| <= 0.5, series converges well
    return _arctan_series(x, 200)


def atan2(y, x):
    """
    Return the arc tangent of y/x in radians.
    The result is in [-pi, pi].
    """
    if x == 0.0:
        if y > 0.0:
            return pi / 2.0
        elif y < 0.0:
            return -pi / 2.0
        else:
            raise ValueError("math domain error: atan2(0, 0) is undefined")
    if x > 0.0:
        return _atan(y / x)
    elif y >= 0.0:
        return _atan(y / x) + pi
    else:
        return _atan(y / x) - pi


# ---------------------------------------------------------------------------
# Verification functions (as described in spec)
# ---------------------------------------------------------------------------

def math2_log_e():
    """abs(log(e) - 1.0) < 1e-9"""
    return abs(log(e) - 1.0) < 1e-9


def math2_log2_eight():
    """log2(8) == 3.0"""
    return log2(8)


def math2_log10_thousand():
    """log10(1000) == 3.0"""
    return log10(1000)


def math2_atan2_one_one():
    """abs(atan2(1.0, 1.0) - pi/4) < 1e-9"""
    return abs(atan2(1.0, 1.0) - pi / 4.0) < 1e-9


def math2_sin_pi_half():
    """sin(pi/2) ≈ 1.0"""
    return abs(sin(pi / 2.0) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    'pi', 'e',
    'log', 'log2', 'log10',
    'sin', 'cos', 'tan', 'atan2',
    'math2_log_e', 'math2_log2_eight', 'math2_log10_thousand',
    'math2_atan2_one_one', 'math2_sin_pi_half',
]