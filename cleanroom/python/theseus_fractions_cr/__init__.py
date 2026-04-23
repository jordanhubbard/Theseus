"""
theseus_fractions_cr — Clean-room fractions module.
No import of the standard `fractions` module.
"""

import math as _math
import operator as _operator


class Fraction:
    """Rational number implementation."""

    __slots__ = ('_numerator', '_denominator')

    def __new__(cls, numerator=0, denominator=None):
        self = super().__new__(cls)
        if denominator is None:
            if isinstance(numerator, int):
                n, d = numerator, 1
            elif isinstance(numerator, float):
                # Convert float to fraction via string
                from decimal import Decimal as _Decimal
                dec = _Decimal(numerator)
                sign, digits, exp = dec.as_tuple()
                n = int(''.join(map(str, digits)))
                if sign:
                    n = -n
                if exp >= 0:
                    n *= 10 ** exp
                    d = 1
                else:
                    d = 10 ** (-exp)
            elif isinstance(numerator, str):
                numerator = numerator.strip()
                if '/' in numerator:
                    num_str, den_str = numerator.split('/', 1)
                    n, d = int(num_str.strip()), int(den_str.strip())
                elif '.' in numerator:
                    int_part, frac_part = numerator.split('.', 1)
                    d = 10 ** len(frac_part)
                    n = int(int_part) * d + int(frac_part)
                else:
                    n, d = int(numerator), 1
            elif isinstance(numerator, Fraction):
                n, d = numerator._numerator, numerator._denominator
            else:
                raise TypeError(f"Cannot convert {type(numerator).__name__} to Fraction")
        else:
            if not isinstance(numerator, int):
                raise TypeError("numerator must be int when denominator is given")
            if not isinstance(denominator, int):
                raise TypeError("denominator must be int")
            n, d = numerator, denominator

        if d == 0:
            raise ZeroDivisionError("Fraction denominator is zero")
        if d < 0:
            n, d = -n, -d
        g = _math.gcd(abs(n), d)
        self._numerator = n // g
        self._denominator = d // g
        return self

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator

    def __repr__(self):
        if self._denominator == 1:
            return f'Fraction({self._numerator!r})'
        return f'Fraction({self._numerator!r}, {self._denominator!r})'

    def __str__(self):
        if self._denominator == 1:
            return str(self._numerator)
        return f'{self._numerator}/{self._denominator}'

    def __float__(self):
        return self._numerator / self._denominator

    def __int__(self):
        return int(self._numerator / self._denominator)

    def __bool__(self):
        return self._numerator != 0

    def __neg__(self):
        return Fraction(-self._numerator, self._denominator)

    def __pos__(self):
        return Fraction(self._numerator, self._denominator)

    def __abs__(self):
        return Fraction(abs(self._numerator), self._denominator)

    def _coerce(self, other):
        if isinstance(other, Fraction):
            return other
        if isinstance(other, int):
            return Fraction(other)
        return NotImplemented

    def __add__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return Fraction(
            self._numerator * other._denominator + other._numerator * self._denominator,
            self._denominator * other._denominator,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return Fraction(
            self._numerator * other._denominator - other._numerator * self._denominator,
            self._denominator * other._denominator,
        )

    def __rsub__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return other.__sub__(self)

    def __mul__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return Fraction(
            self._numerator * other._numerator,
            self._denominator * other._denominator,
        )

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return Fraction(
            self._numerator * other._denominator,
            self._denominator * other._numerator,
        )

    def __rtruediv__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return other.__truediv__(self)

    def __floordiv__(self, other):
        return int(self.__truediv__(other))

    def __mod__(self, other):
        div = self.__floordiv__(other)
        return self - other * div

    def __pow__(self, exp):
        if isinstance(exp, int):
            if exp >= 0:
                return Fraction(self._numerator ** exp, self._denominator ** exp)
            else:
                return Fraction(self._denominator ** (-exp), self._numerator ** (-exp))
        return float(self) ** exp

    def __eq__(self, other):
        if isinstance(other, Fraction):
            return self._numerator == other._numerator and self._denominator == other._denominator
        if isinstance(other, int):
            return self._denominator == 1 and self._numerator == other
        if isinstance(other, float):
            return float(self) == other
        return NotImplemented

    def __lt__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return self._numerator * other._denominator < other._numerator * self._denominator

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        other = self._coerce(other)
        if other is NotImplemented:
            return NotImplemented
        return self._numerator * other._denominator > other._numerator * self._denominator

    def __ge__(self, other):
        return self == other or self > other

    def __hash__(self):
        return hash((self._numerator, self._denominator))

    def limit_denominator(self, max_denominator=10**6):
        """Find closest fraction with denominator at most max_denominator."""
        if max_denominator < 1:
            raise ValueError("max_denominator should be at least 1")
        if self._denominator <= max_denominator:
            return Fraction(self._numerator, self._denominator)
        p0, q0, p1, q1 = 0, 1, 1, 0
        n, d = self._numerator, self._denominator
        while True:
            a = n // d
            q2 = q0 + a * q1
            if q2 > max_denominator:
                break
            p0, q0, p1, q1 = p1, q1, p0 + a * p1, q2
            n, d = d, n - a * d
        k = (max_denominator - q0) // q1
        bound1 = Fraction(p0 + k * p1, q0 + k * q1)
        bound2 = Fraction(p1, q1)
        if abs(bound2 - self) <= abs(bound1 - self):
            return bound2
        return bound1

    @classmethod
    def from_float(cls, f):
        """Construct from float."""
        return cls(f)

    @classmethod
    def from_decimal(cls, dec):
        """Construct from Decimal."""
        sign, digits, exp = dec.as_tuple()
        n = int(''.join(map(str, digits)))
        if sign:
            n = -n
        if exp >= 0:
            n *= 10 ** exp
            d = 1
        else:
            d = 10 ** (-exp)
        return cls(n, d)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def fractions2_create():
    """Fraction(1, 2) has numerator=1, denominator=2; returns True."""
    f = Fraction(1, 2)
    return f.numerator == 1 and f.denominator == 2


def fractions2_add():
    """Fraction(1,3) + Fraction(1,6) == Fraction(1,2); returns True."""
    return Fraction(1, 3) + Fraction(1, 6) == Fraction(1, 2)


def fractions2_reduce():
    """Fraction(6,4) reduces to Fraction(3,2); returns True."""
    f = Fraction(6, 4)
    return f.numerator == 3 and f.denominator == 2


__all__ = [
    'Fraction',
    'fractions2_create', 'fractions2_add', 'fractions2_reduce',
]
