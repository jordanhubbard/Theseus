from abc import ABCMeta, abstractmethod


class Number(metaclass=ABCMeta):
    """Abstract base class for all numbers."""
    pass


class Complex(Number):
    """Abstract base class for complex numbers."""
    pass


class Real(Complex):
    """Abstract base class for real numbers."""
    pass


class Rational(Real):
    """Abstract base class for rational numbers."""
    pass


class Integral(Rational):
    """Abstract base class for integral numbers."""
    pass


# Register built-in types
Complex.register(complex)
Real.register(float)
Integral.register(int)


def numbers2_int_is_integral():
    return isinstance(5, Integral)


def numbers2_float_is_real():
    return isinstance(3.14, Real)


def numbers2_complex_is_complex():
    return isinstance(1+2j, Complex)


__all__ = [
    'Number',
    'Complex',
    'Real',
    'Rational',
    'Integral',
    'numbers2_int_is_integral',
    'numbers2_float_is_real',
    'numbers2_complex_is_complex',
]