def _gcd(a, b):
    """Compute the greatest common divisor of a and b."""
    while b:
        a, b = b, a % b
    return a


class Fraction:
    """A rational number stored in reduced form."""

    def __init__(self, numerator=0, denominator=1):
        if denominator == 0:
            raise ZeroDivisionError("Fraction denominator cannot be zero")
        
        # Handle sign: keep denominator positive
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        
        # Reduce using GCD
        if numerator == 0:
            self._numerator = 0
            self._denominator = 1
        else:
            common = _gcd(abs(numerator), abs(denominator))
            self._numerator = numerator // common
            self._denominator = denominator // common

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator

    def __add__(self, other):
        if isinstance(other, Fraction):
            new_num = self._numerator * other._denominator + other._numerator * self._denominator
            new_den = self._denominator * other._denominator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Fraction):
            new_num = self._numerator * other._denominator - other._numerator * self._denominator
            new_den = self._denominator * other._denominator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, Fraction):
            new_num = self._numerator * other._numerator
            new_den = self._denominator * other._denominator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Fraction):
            if other._numerator == 0:
                raise ZeroDivisionError("Division by zero fraction")
            new_num = self._numerator * other._denominator
            new_den = self._denominator * other._numerator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Fraction):
            return self._numerator == other._numerator and self._denominator == other._denominator
        return NotImplemented

    def __repr__(self):
        return f"Fraction({self._numerator}, {self._denominator})"

    def __str__(self):
        if self._denominator == 1:
            return str(self._numerator)
        return f"{self._numerator}/{self._denominator}"

    def __neg__(self):
        return Fraction(-self._numerator, self._denominator)

    def __pos__(self):
        return Fraction(self._numerator, self._denominator)

    def __abs__(self):
        return Fraction(abs(self._numerator), self._denominator)

    def __hash__(self):
        return hash((self._numerator, self._denominator))


def fractions_add():
    """Test that Fraction(1, 2) + Fraction(1, 3) == Fraction(5, 6)."""
    result = Fraction(1, 2) + Fraction(1, 3)
    expected = Fraction(5, 6)
    return result == expected


def fractions_reduce():
    """Test that Fraction(2, 4) reduces to Fraction(1, 2)."""
    f = Fraction(2, 4)
    return f.numerator == 1 and f.denominator == 2


def fractions_multiply():
    """Test that Fraction(1, 2) * Fraction(2, 3) == Fraction(1, 3)."""
    result = Fraction(1, 2) * Fraction(2, 3)
    expected = Fraction(1, 3)
    return result == expected