# theseus_math_cr — clean-room math module (no `import math`)
# Implements sqrt, constants (pi, e), and trig (sin, cos, tan) from scratch.

# ---------------------------------------------------------------------------
# Constants (computed without importing math)
# ---------------------------------------------------------------------------

def _compute_pi():
    # Machin's formula: pi/4 = 4*arctan(1/5) - arctan(1/239)
    # arctan(x) = sum_{k=0..inf} (-1)^k * x^(2k+1) / (2k+1)
    def arctan_recip(n, terms=60):
        # arctan(1/n) using the series; n is integer
        # Use rationals via floats; high enough precision for double.
        x2 = 1.0 / (n * n)
        term = 1.0 / n
        total = 0.0
        sign = 1
        for k in range(terms):
            total += sign * term / (2 * k + 1)
            term *= x2
            sign = -sign
        return total
    return 16.0 * arctan_recip(5) - 4.0 * arctan_recip(239)


def _compute_e():
    # e = sum_{k=0..inf} 1/k!
    total = 0.0
    fact = 1.0
    for k in range(1, 25):
        total += 1.0 / fact
        fact *= k
    return total + 1.0 / fact  # add a final term for tail; ensures ~double precision


PI = _compute_pi()
E = _compute_e()
TAU = 2.0 * PI
HALF_PI = PI / 2.0


# ---------------------------------------------------------------------------
# sqrt — Newton's method with bit-twiddling seed
# ---------------------------------------------------------------------------

def sqrt(x):
    if x < 0:
        raise ValueError("sqrt of negative number")
    if x == 0:
        return 0.0
    # Initial guess via repeated halving of exponent
    guess = x if x >= 1.0 else 1.0
    # Bring guess into a reasonable range
    while guess * guess > x * 4.0:
        guess *= 0.5
    while guess * guess * 4.0 < x:
        guess *= 2.0
    # Newton iterations: g = (g + x/g) / 2
    for _ in range(60):
        new_guess = 0.5 * (guess + x / guess)
        if new_guess == guess:
            break
        guess = new_guess
    return guess


# ---------------------------------------------------------------------------
# Trig — sin, cos, tan via range reduction + Taylor series
# ---------------------------------------------------------------------------

def _reduce_angle(x):
    # Reduce x into [-pi, pi]
    # Use repeated subtraction of TAU
    while x > PI:
        x -= TAU
    while x < -PI:
        x += TAU
    return x


def sin(x):
    x = _reduce_angle(float(x))
    # Further reduce to [-pi/2, pi/2] using sin(pi - x) = sin(x), sin(-pi - x) = sin(x)
    if x > HALF_PI:
        x = PI - x
    elif x < -HALF_PI:
        x = -PI - x
    # Taylor series: sin(x) = x - x^3/3! + x^5/5! - ...
    x2 = x * x
    term = x
    total = 0.0
    sign = 1
    denom = 1.0
    k = 1
    for i in range(25):
        total += sign * term / denom
        term *= x2
        denom *= (k + 1) * (k + 2)
        k += 2
        sign = -sign
    return total


def cos(x):
    x = _reduce_angle(float(x))
    # cos is even; reduce to [0, pi]
    if x < 0:
        x = -x
    # cos(pi - x) = -cos(x); reduce to [0, pi/2]
    flip = False
    if x > HALF_PI:
        x = PI - x
        flip = True
    # Taylor: cos(x) = 1 - x^2/2! + x^4/4! - ...
    x2 = x * x
    term = 1.0
    total = 0.0
    sign = 1
    denom = 1.0
    k = 0
    for i in range(25):
        total += sign * term / denom
        term *= x2
        denom *= (k + 1) * (k + 2)
        k += 2
        sign = -sign
    if flip:
        total = -total
    return total


def tan(x):
    c = cos(x)
    if c == 0:
        raise ValueError("tan undefined")
    return sin(x) / c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fabs(x):
    return -x if x < 0 else x


def _close(a, b, tol=1e-9):
    return _fabs(a - b) < tol


# ---------------------------------------------------------------------------
# Invariant predicates
# ---------------------------------------------------------------------------

def math2_sqrt():
    # Exact / known cases
    if sqrt(0) != 0.0:
        return False
    if sqrt(1) != 1.0:
        return False
    if not _close(sqrt(4), 2.0):
        return False
    if not _close(sqrt(9), 3.0):
        return False
    if not _close(sqrt(16), 4.0):
        return False
    if not _close(sqrt(2), 1.4142135623730951, 1e-9):
        return False
    if not _close(sqrt(2.25), 1.5):
        return False
    # Inverse property
    for v in (0.5, 1.7, 12345.6789, 1e-6, 1e6):
        r = sqrt(v)
        if not _close(r * r, v, _fabs(v) * 1e-9 + 1e-12):
            return False
    # Negative raises
    try:
        sqrt(-1.0)
        return False
    except ValueError:
        pass
    return True


def math2_constants():
    if not _close(PI, 3.141592653589793, 1e-10):
        return False
    if not _close(E, 2.718281828459045, 1e-10):
        return False
    if not _close(TAU, 2.0 * 3.141592653589793, 1e-10):
        return False
    # Identity: e^(i*pi) flavor — sin(pi) ~ 0, cos(pi) ~ -1
    if not _close(sin(PI), 0.0, 1e-9):
        return False
    if not _close(cos(PI), -1.0, 1e-9):
        return False
    return True


def math2_trig():
    # Known angles
    if not _close(sin(0.0), 0.0, 1e-12):
        return False
    if not _close(cos(0.0), 1.0, 1e-12):
        return False
    if not _close(sin(HALF_PI), 1.0, 1e-9):
        return False
    if not _close(cos(HALF_PI), 0.0, 1e-9):
        return False
    if not _close(sin(PI), 0.0, 1e-9):
        return False
    if not _close(cos(PI), -1.0, 1e-9):
        return False
    # Pythagorean identity at various angles
    test_points = [0.1, 0.5, 1.0, 1.3, -0.7, 2.5, -3.1, 5.0, -8.4]
    for t in test_points:
        s = sin(t)
        c = cos(t)
        if not _close(s * s + c * c, 1.0, 1e-9):
            return False
    # tan = sin/cos
    for t in (0.3, 1.1, -0.9, 2.0):
        if not _close(tan(t), sin(t) / cos(t), 1e-9):
            return False
    # sin is odd, cos is even
    for t in (0.4, 1.7, 3.0):
        if not _close(sin(-t), -sin(t), 1e-9):
            return False
        if not _close(cos(-t), cos(t), 1e-9):
            return False
    # Compare against known double-precision values
    if not _close(sin(1.0), 0.8414709848078965, 1e-9):
        return False
    if not _close(cos(1.0), 0.5403023058681398, 1e-9):
        return False
    return True


__all__ = [
    "PI", "E", "TAU", "HALF_PI",
    "sqrt", "sin", "cos", "tan",
    "math2_sqrt", "math2_constants", "math2_trig",
]