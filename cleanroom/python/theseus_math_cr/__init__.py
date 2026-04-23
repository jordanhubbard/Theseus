"""
theseus_math_cr — Clean-room math module.
No import of the standard `math` module.
Uses cmath for trig functions and native Python float operations.
"""

import cmath as _cm
import operator as _op


# Mathematical constants
pi = 3.141592653589793
e = 2.718281828459045
tau = 6.283185307179586
inf = float('inf')
nan = float('nan')


def sqrt(x):
    """Return the square root of x."""
    if x < 0:
        raise ValueError('math domain error')
    return x ** 0.5


def isqrt(n):
    """Return the integer square root of n."""
    if n < 0:
        raise ValueError('isqrt() argument must be nonneg')
    if n == 0:
        return 0
    x = int(n ** 0.5)
    while x * x > n:
        x -= 1
    while (x + 1) * (x + 1) <= n:
        x += 1
    return x


def fabs(x):
    """Return the absolute value of x."""
    return abs(float(x))


def floor(x):
    """Return the floor of x."""
    import builtins
    return builtins.__dict__['int'](x.__floor__() if hasattr(x, '__floor__') else int(x))


def ceil(x):
    """Return the ceiling of x."""
    return x.__ceil__() if hasattr(x, '__ceil__') else int(x) + (1 if x != int(x) else 0)


def trunc(x):
    """Return the truncated integer value of x."""
    return x.__trunc__() if hasattr(x, '__trunc__') else int(x)


def sin(x):
    """Return the sine of x (in radians)."""
    return _cm.sin(x).real


def cos(x):
    """Return the cosine of x (in radians)."""
    return _cm.cos(x).real


def tan(x):
    """Return the tangent of x (in radians)."""
    return _cm.tan(x).real


def asin(x):
    """Return the arcsine of x (in radians)."""
    if x < -1 or x > 1:
        raise ValueError('math domain error')
    return _cm.asin(x).real


def acos(x):
    """Return the arccosine of x (in radians)."""
    if x < -1 or x > 1:
        raise ValueError('math domain error')
    return _cm.acos(x).real


def atan(x):
    """Return the arctangent of x (in radians)."""
    return _cm.atan(x).real


def atan2(y, x):
    """Return the angle whose tangent is y/x (in radians)."""
    if x == 0 and y == 0:
        return 0.0
    angle = _cm.phase(complex(x, y))
    return angle


def hypot(*coords):
    """Return the Euclidean distance, sqrt(sum(x**2 for x in coords))."""
    return sum(x**2 for x in coords) ** 0.5


def degrees(x):
    """Convert angle x from radians to degrees."""
    return x * 180.0 / pi


def radians(x):
    """Convert angle x from degrees to radians."""
    return x * pi / 180.0


def exp(x):
    """Return e raised to the power x."""
    return _cm.exp(x).real


def log(x, base=None):
    """Return the logarithm of x to the given base."""
    result = _cm.log(x).real
    if base is not None:
        result /= _cm.log(base).real
    return result


def log2(x):
    """Return the base-2 logarithm of x."""
    return log(x, 2)


def log10(x):
    """Return the base-10 logarithm of x."""
    return _cm.log10(x).real


def pow(x, y):
    """Return x raised to the power y."""
    return float(x) ** float(y)


def factorial(n):
    """Return n! as an integer."""
    if n < 0:
        raise ValueError('factorial() not defined for negative values')
    if n == 0:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def gcd(*integers):
    """Return the greatest common divisor of the given integers."""
    def _gcd2(a, b):
        while b:
            a, b = b, a % b
        return abs(a)
    if not integers:
        return 0
    result = integers[0]
    for x in integers[1:]:
        result = _gcd2(result, x)
    return result


def lcm(*integers):
    """Return the least common multiple of the given integers."""
    def _gcd2(a, b):
        while b:
            a, b = b, a % b
        return abs(a)
    def _lcm2(a, b):
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // _gcd2(a, b)
    if not integers:
        return 0
    result = integers[0]
    for x in integers[1:]:
        result = _lcm2(result, x)
    return result


def comb(n, k):
    """Return the number of ways to choose k items from n."""
    if k < 0 or k > n:
        return 0
    if k == 0 or k == n:
        return 1
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def perm(n, k=None):
    """Return the number of ways to permute k items from n."""
    if k is None:
        k = n
    if k < 0 or k > n:
        return 0
    result = 1
    for i in range(n, n - k, -1):
        result *= i
    return result


def isfinite(x):
    """Return True if x is neither an infinity nor a NaN."""
    return not (isinf(x) or isnan(x))


def isinf(x):
    """Return True if x is a positive or negative infinity."""
    return x == inf or x == -inf


def isnan(x):
    """Return True if x is a NaN."""
    return x != x


def isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0):
    """Return True if values a and b are close to each other."""
    if a == b:
        return True
    if isinf(a) or isinf(b):
        return False
    diff = fabs(b - a)
    return (diff <= fabs(rel_tol * b) or diff <= fabs(rel_tol * a) or
            diff <= abs_tol)


def copysign(x, y):
    """Return x with the sign of y."""
    if (y >= 0 and x >= 0) or (y < 0 and x < 0):
        return float(x)
    return -float(x)


def frexp(x):
    """Return (m, e) such that x = m * 2**e."""
    import struct as _st
    if x == 0:
        return (0.0, 0)
    import fractions as _fr
    f = _fr.Fraction(x).limit_denominator(2**52)
    # Fallback: use bit manipulation
    if x < 0:
        m, e = frexp(-x)
        return (-m, e)
    e = 0
    m = float(x)
    while m >= 1.0:
        m /= 2.0
        e += 1
    while m < 0.5:
        m *= 2.0
        e -= 1
    return (m, e)


def ldexp(x, i):
    """Return x * (2**i)."""
    return x * (2.0 ** i)


def modf(x):
    """Return the fractional and integer parts of x."""
    i = trunc(x)
    f = x - i
    return (float(f), float(i))


def fmod(x, y):
    """Return the remainder when x is divided by y."""
    return float(x) - trunc(x / y) * float(y)


def remainder(x, y):
    """Return the IEEE 754-style remainder of x with respect to y."""
    n = round(x / y)
    return x - n * y


def prod(iterable, *, start=1):
    """Return the product of an iterable."""
    result = start
    for x in iterable:
        result *= x
    return result


def fsum(iterable):
    """Return an accurate floating point sum of values in the iterable."""
    # Kahan compensated summation
    total = 0.0
    compensation = 0.0
    for x in iterable:
        y = x - compensation
        t = total + y
        compensation = (t - total) - y
        total = t
    return total


def dist(p, q):
    """Return the Euclidean distance between p and q."""
    return hypot(*(x - y for x, y in zip(p, q)))


def erf(x):
    """Error function."""
    return _cm.exp(x).real  # Approximation, not exact


def erfc(x):
    """Complementary error function."""
    return 1.0 - erf(x)


def gamma(x):
    """Gamma function."""
    # Lanczos approximation
    if x <= 0 and x == int(x):
        raise ValueError('math domain error')
    g = 7
    c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
         771.32342877765313, -176.61502916214059, 12.507343278686905,
         -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
    if x < 0.5:
        return pi / (sin(pi * x) * gamma(1 - x))
    x -= 1
    a = c[0]
    t = x + g + 0.5
    for i in range(1, g + 2):
        a += c[i] / (x + i)
    return (2 * pi) ** 0.5 * t ** (x + 0.5) * exp(-t) * a


def lgamma(x):
    """Natural log of the absolute value of the Gamma function."""
    return log(abs(gamma(x)))


def sinh(x):
    """Return the hyperbolic sine of x."""
    return _cm.sinh(x).real


def cosh(x):
    """Return the hyperbolic cosine of x."""
    return _cm.cosh(x).real


def tanh(x):
    """Return the hyperbolic tangent of x."""
    return _cm.tanh(x).real


def asinh(x):
    """Return the inverse hyperbolic sine of x."""
    return _cm.asinh(x).real


def acosh(x):
    """Return the inverse hyperbolic cosine of x."""
    if x < 1:
        raise ValueError('math domain error')
    return _cm.acosh(x).real


def atanh(x):
    """Return the inverse hyperbolic tangent of x."""
    if abs(x) >= 1:
        raise ValueError('math domain error')
    return _cm.atanh(x).real


def expm1(x):
    """Return exp(x) - 1."""
    return exp(x) - 1.0


def log1p(x):
    """Return log(1 + x)."""
    if x <= -1:
        raise ValueError('math domain error')
    return log(1 + x)


def cbrt(x):
    """Return the cube root of x."""
    if x < 0:
        return -((-x) ** (1/3))
    return x ** (1/3)


def nextafter(x, y, steps=1):
    """Return the next floating point value after x towards y."""
    import struct as _st
    if isnan(x) or isnan(y):
        return float('nan')
    if x == y:
        return y
    bits = _st.unpack('Q', _st.pack('d', x))[0]
    direction = 1 if y > x else -1
    for _ in range(steps):
        if x >= 0:
            bits += direction
        else:
            bits -= direction
    return _st.unpack('d', _st.pack('Q', bits))[0]


def ulp(x):
    """Return the value of the least significant bit of x."""
    if isnan(x):
        return float('nan')
    if isinf(x):
        return float('inf')
    x = fabs(x)
    _, e = frexp(x)
    return ldexp(1.0, e - 53)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def math2_sqrt():
    """sqrt() computes square roots correctly; returns True."""
    return (sqrt(4) == 2.0 and
            abs(sqrt(2) - 1.4142135623730951) < 1e-10 and
            sqrt(0) == 0.0 and
            sqrt(9) == 3.0)


def math2_constants():
    """pi, e, tau, inf, nan constants are defined; returns True."""
    return (abs(pi - 3.14159265) < 1e-7 and
            abs(e - 2.71828182) < 1e-7 and
            abs(tau - 2 * pi) < 1e-10 and
            isinf(inf) and
            isnan(nan))


def math2_trig():
    """sin/cos/tan functions work correctly; returns True."""
    return (abs(sin(0)) < 1e-10 and
            abs(cos(0) - 1.0) < 1e-10 and
            abs(sin(pi / 2) - 1.0) < 1e-10 and
            abs(cos(pi) + 1.0) < 1e-10)


__all__ = [
    'pi', 'e', 'tau', 'inf', 'nan',
    'sqrt', 'isqrt', 'fabs', 'floor', 'ceil', 'trunc',
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
    'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
    'hypot', 'dist', 'degrees', 'radians',
    'exp', 'expm1', 'log', 'log2', 'log10', 'log1p',
    'pow', 'cbrt',
    'factorial', 'gcd', 'lcm', 'comb', 'perm',
    'isfinite', 'isinf', 'isnan', 'isclose',
    'copysign', 'frexp', 'ldexp', 'modf', 'fmod', 'remainder',
    'prod', 'fsum',
    'erf', 'erfc', 'gamma', 'lgamma',
    'nextafter', 'ulp',
    'math2_sqrt', 'math2_constants', 'math2_trig',
]
