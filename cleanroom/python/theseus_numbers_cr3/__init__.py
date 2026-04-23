"""
theseus_numbers_cr3 - Clean-room implementation of numeric tower abstract base classes.
Do NOT import the 'numbers' module.
"""

import abc


class Number(metaclass=abc.ABCMeta):
    """Abstract base class for all numbers in the numeric tower."""
    __slots__ = ()


class Complex(Number):
    """Abstract base class for complex numbers."""
    __slots__ = ()

    @abc.abstractmethod
    def __complex__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def real(self):
        raise NotImplementedError

    @abc.abstractmethod
    def imag(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __add__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __radd__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __neg__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __pos__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __mul__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rmul__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __truediv__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rtruediv__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __pow__(self, exponent):
        raise NotImplementedError

    @abc.abstractmethod
    def __rpow__(self, base):
        raise NotImplementedError

    @abc.abstractmethod
    def __abs__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def conjugate(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError


class Real(Complex):
    """Abstract base class for real numbers."""
    __slots__ = ()

    @abc.abstractmethod
    def __float__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __trunc__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __floor__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __ceil__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __round__(self, ndigits=None):
        raise NotImplementedError

    @abc.abstractmethod
    def __floordiv__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rfloordiv__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __mod__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rmod__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __lt__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __le__(self, other):
        raise NotImplementedError


class Rational(Real):
    """Abstract base class for rational numbers."""
    __slots__ = ()

    @property
    @abc.abstractmethod
    def numerator(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def denominator(self):
        raise NotImplementedError


class Integral(Rational):
    """Abstract base class for integral numbers."""
    __slots__ = ()

    @abc.abstractmethod
    def __int__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __index__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __pow__(self, exponent, modulus=None):
        raise NotImplementedError

    @abc.abstractmethod
    def __lshift__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rlshift__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rshift__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rrshift__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __and__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rand__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __xor__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __rxor__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __or__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __ror__(self, other):
        raise NotImplementedError

    @abc.abstractmethod
    def __invert__(self):
        raise NotImplementedError


# Register Python built-in types with the numeric tower
# int -> Integral (and by inheritance: Rational, Real, Complex, Number)
Integral.register(int)

# float -> Real (and by inheritance: Complex, Number)
Real.register(float)

# complex -> Complex (and by inheritance: Number)
Complex.register(complex)


# ─── Invariant functions ───────────────────────────────────────────────────────

def numbers3_integral_isinstance() -> bool:
    """isinstance(5, Integral) == True because int is registered with Integral."""
    return isinstance(5, Integral)


def numbers3_real_isinstance() -> bool:
    """isinstance(5.0, Real) == True because float is registered with Real."""
    return isinstance(5.0, Real)


def numbers3_complex_isinstance() -> bool:
    """isinstance(1+2j, Complex) == True because complex is registered with Complex."""
    return isinstance(1 + 2j, Complex)