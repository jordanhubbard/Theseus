"""
theseus_numbers_cr: Clean-room numeric tower ABCs.
Do NOT import the `numbers` module.
"""

import abc


class Number(metaclass=abc.ABCMeta):
    """Abstract base class for all numbers."""

    @abc.abstractmethod
    def __abs__(self):
        ...

    @classmethod
    def __subclasshook__(cls, C):
        # Any class is potentially a Number; defer to registration
        return NotImplemented


class Complex(Number):
    """Abstract base class for complex numbers."""

    @property
    @abc.abstractmethod
    def real(self):
        ...

    @property
    @abc.abstractmethod
    def imag(self):
        ...

    @abc.abstractmethod
    def __complex__(self):
        ...

    @abc.abstractmethod
    def __add__(self, other):
        ...

    @abc.abstractmethod
    def __radd__(self, other):
        ...

    @abc.abstractmethod
    def __neg__(self):
        ...

    @abc.abstractmethod
    def __pos__(self):
        ...

    @abc.abstractmethod
    def __mul__(self, other):
        ...

    @abc.abstractmethod
    def __rmul__(self, other):
        ...

    @abc.abstractmethod
    def __truediv__(self, other):
        ...

    @abc.abstractmethod
    def __rtruediv__(self, other):
        ...

    @abc.abstractmethod
    def __pow__(self, exponent):
        ...

    @abc.abstractmethod
    def __rpow__(self, base):
        ...

    @abc.abstractmethod
    def __abs__(self):
        ...

    @abc.abstractmethod
    def conjugate(self):
        ...

    @abc.abstractmethod
    def __eq__(self, other):
        ...

    @classmethod
    def __subclasshook__(cls, C):
        return NotImplemented


class Real(Complex):
    """Abstract base class for real numbers."""

    @abc.abstractmethod
    def __float__(self):
        ...

    @abc.abstractmethod
    def __trunc__(self):
        ...

    @abc.abstractmethod
    def __floor__(self):
        ...

    @abc.abstractmethod
    def __ceil__(self):
        ...

    @abc.abstractmethod
    def __round__(self, ndigits=None):
        ...

    @abc.abstractmethod
    def __floordiv__(self, other):
        ...

    @abc.abstractmethod
    def __rfloordiv__(self, other):
        ...

    @abc.abstractmethod
    def __mod__(self, other):
        ...

    @abc.abstractmethod
    def __rmod__(self, other):
        ...

    @abc.abstractmethod
    def __lt__(self, other):
        ...

    @abc.abstractmethod
    def __le__(self, other):
        ...

    @classmethod
    def __subclasshook__(cls, C):
        return NotImplemented


class Rational(Real):
    """Abstract base class for rational numbers."""

    @property
    @abc.abstractmethod
    def numerator(self):
        ...

    @property
    @abc.abstractmethod
    def denominator(self):
        ...

    @classmethod
    def __subclasshook__(cls, C):
        return NotImplemented


class Integral(Rational):
    """Abstract base class for integers."""

    @abc.abstractmethod
    def __int__(self):
        ...

    @abc.abstractmethod
    def __index__(self):
        ...

    @abc.abstractmethod
    def __pow__(self, exponent, modulus=None):
        ...

    @abc.abstractmethod
    def __lshift__(self, other):
        ...

    @abc.abstractmethod
    def __rlshift__(self, other):
        ...

    @abc.abstractmethod
    def __rshift__(self, other):
        ...

    @abc.abstractmethod
    def __rrshift__(self, other):
        ...

    @abc.abstractmethod
    def __and__(self, other):
        ...

    @abc.abstractmethod
    def __rand__(self, other):
        ...

    @abc.abstractmethod
    def __xor__(self, other):
        ...

    @abc.abstractmethod
    def __rxor__(self, other):
        ...

    @abc.abstractmethod
    def __or__(self, other):
        ...

    @abc.abstractmethod
    def __ror__(self, other):
        ...

    @abc.abstractmethod
    def __invert__(self):
        ...

    @classmethod
    def __subclasshook__(cls, C):
        return NotImplemented


# ---------------------------------------------------------------------------
# Register built-in Python types with the ABCs
# ---------------------------------------------------------------------------

# Register `complex` with Complex
Complex.register(complex)

# Register `float` with Real
Real.register(float)

# Register `int` with Integral (which inherits from Rational -> Real -> Complex -> Number)
Integral.register(int)

# Also register bool (subclass of int) — it gets picked up automatically via int


# ---------------------------------------------------------------------------
# Required exported functions
# ---------------------------------------------------------------------------

def numbers_int_is_integral():
    """isinstance(42, Integral) == True"""
    return isinstance(42, Integral)


def numbers_float_is_real():
    """isinstance(3.14, Real) == True"""
    return isinstance(3.14, Real)


def numbers_int_is_complex():
    """isinstance(1, Complex) == True"""
    return isinstance(1, Complex)


__all__ = [
    "Number",
    "Complex",
    "Real",
    "Rational",
    "Integral",
    "numbers_int_is_integral",
    "numbers_float_is_real",
    "numbers_int_is_complex",
]