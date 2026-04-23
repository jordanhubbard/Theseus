"""
theseus_cmath_cr — Clean-room cmath module.
No import of the standard `cmath` module.
"""

import math as _math

pi = _math.pi
e = _math.e
tau = 2 * _math.pi
inf = float('inf')
nan = float('nan')
infj = complex(0, float('inf'))
nanj = complex(0, float('nan'))


def phase(z):
    """Return the phase (argument) of z in radians."""
    z = complex(z)
    return _math.atan2(z.imag, z.real)


def polar(z):
    """Return the representation of z in polar coordinates (r, phi)."""
    z = complex(z)
    return abs(z), phase(z)


def rect(r, phi):
    """Return the complex number z with modulus r and phase phi."""
    return complex(r * _math.cos(phi), r * _math.sin(phi))


def exp(z):
    """Return e**z."""
    z = complex(z)
    return complex(_math.e ** z.real * _math.cos(z.imag),
                   _math.e ** z.real * _math.sin(z.imag))


def log(z, base=None):
    """Return the logarithm of z."""
    z = complex(z)
    r, phi = polar(z)
    if r == 0:
        raise ValueError("math domain error")
    result = complex(_math.log(r), phi)
    if base is not None:
        result /= log(base)
    return result


def log10(z):
    """Return the base-10 logarithm of z."""
    return log(z, 10)


def sqrt(z):
    """Return the square root of z."""
    z = complex(z)
    if z.imag == 0 and z.real >= 0:
        return complex(_math.sqrt(z.real), 0)
    r, phi = polar(z)
    return rect(_math.sqrt(r), phi / 2)


def sin(z):
    """Return the sine of z."""
    z = complex(z)
    return complex(_math.sin(z.real) * _math.cosh(z.imag),
                   _math.cos(z.real) * _math.sinh(z.imag))


def cos(z):
    """Return the cosine of z."""
    z = complex(z)
    return complex(_math.cos(z.real) * _math.cosh(z.imag),
                   -_math.sin(z.real) * _math.sinh(z.imag))


def tan(z):
    """Return the tangent of z."""
    return sin(z) / cos(z)


def asin(z):
    """Return the arc sine of z."""
    z = complex(z)
    i = complex(0, 1)
    return -i * log(i * z + sqrt(1 - z * z))


def acos(z):
    """Return the arc cosine of z."""
    z = complex(z)
    i = complex(0, 1)
    return -i * log(z + i * sqrt(1 - z * z))


def atan(z):
    """Return the arc tangent of z."""
    z = complex(z)
    i = complex(0, 1)
    return (i / 2) * (log(1 - i * z) - log(1 + i * z))


def sinh(z):
    """Return the hyperbolic sine of z."""
    z = complex(z)
    return complex(_math.sinh(z.real) * _math.cos(z.imag),
                   _math.cosh(z.real) * _math.sin(z.imag))


def cosh(z):
    """Return the hyperbolic cosine of z."""
    z = complex(z)
    return complex(_math.cosh(z.real) * _math.cos(z.imag),
                   _math.sinh(z.real) * _math.sin(z.imag))


def tanh(z):
    """Return the hyperbolic tangent of z."""
    return sinh(z) / cosh(z)


def isnan(z):
    """Return True if both real and imaginary parts are NaN."""
    z = complex(z)
    return _math.isnan(z.real) or _math.isnan(z.imag)


def isinf(z):
    """Return True if either real or imaginary part is infinite."""
    z = complex(z)
    return _math.isinf(z.real) or _math.isinf(z.imag)


def isfinite(z):
    """Return True if both real and imaginary parts are finite."""
    z = complex(z)
    return _math.isfinite(z.real) and _math.isfinite(z.imag)


def isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0):
    """Return True if a and b are close."""
    a, b = complex(a), complex(b)
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def cmath2_polar():
    """polar(1+0j) returns (1.0, 0.0); returns True."""
    r, phi = polar(1 + 0j)
    return abs(r - 1.0) < 1e-10 and abs(phi) < 1e-10


def cmath2_rect():
    """rect(1.0, 0.0) returns 1+0j; returns True."""
    z = rect(1.0, 0.0)
    return abs(z.real - 1.0) < 1e-10 and abs(z.imag) < 1e-10


def cmath2_phase():
    """phase(-1+0j) is approximately pi; returns True."""
    return abs(phase(-1 + 0j) - _math.pi) < 1e-10


__all__ = [
    'pi', 'e', 'tau', 'inf', 'nan', 'infj', 'nanj',
    'phase', 'polar', 'rect',
    'exp', 'log', 'log10', 'sqrt',
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
    'sinh', 'cosh', 'tanh',
    'isnan', 'isinf', 'isfinite', 'isclose',
    'cmath2_polar', 'cmath2_rect', 'cmath2_phase',
]
