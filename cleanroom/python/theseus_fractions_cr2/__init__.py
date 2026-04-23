import math


class Fraction:
    def __init__(self, numerator=0, denominator=1):
        if denominator == 0:
            raise ZeroDivisionError("Fraction denominator cannot be zero")
        
        if isinstance(numerator, float):
            # Convert float to fraction
            # Use the float's as_integer_ratio method
            n, d = numerator.as_integer_ratio()
            numerator = n
            denominator = d * denominator
        
        if isinstance(denominator, float):
            n, d = denominator.as_integer_ratio()
            numerator = numerator * d
            denominator = n
        
        # Handle sign
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        
        # Reduce
        g = math.gcd(abs(numerator), abs(denominator))
        self._numerator = numerator // g
        self._denominator = denominator // g

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator

    def __repr__(self):
        if self._denominator == 1:
            return f"Fraction({self._numerator}, 1)"
        return f"Fraction({self._numerator}, {self._denominator})"

    def __str__(self):
        if self._denominator == 1:
            return str(self._numerator)
        return f"{self._numerator}/{self._denominator}"

    def __eq__(self, other):
        if isinstance(other, Fraction):
            return self._numerator == other._numerator and self._denominator == other._denominator
        if isinstance(other, int):
            return self._numerator == other and self._denominator == 1
        if isinstance(other, float):
            return float(self) == other
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Fraction):
            return self._numerator * other._denominator < other._numerator * self._denominator
        if isinstance(other, int):
            return self._numerator < other * self._denominator
        return NotImplemented

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        if isinstance(other, Fraction):
            return self._numerator * other._denominator > other._numerator * self._denominator
        if isinstance(other, int):
            return self._numerator > other * self._denominator
        return NotImplemented

    def __ge__(self, other):
        return self == other or self > other

    def __add__(self, other):
        if isinstance(other, int):
            other = Fraction(other)
        if isinstance(other, Fraction):
            new_num = self._numerator * other._denominator + other._numerator * self._denominator
            new_den = self._denominator * other._denominator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, int):
            other = Fraction(other)
        if isinstance(other, Fraction):
            new_num = self._numerator * other._denominator - other._numerator * self._denominator
            new_den = self._denominator * other._denominator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, int):
            other = Fraction(other)
        return other.__sub__(self)

    def __mul__(self, other):
        if isinstance(other, int):
            other = Fraction(other)
        if isinstance(other, Fraction):
            new_num = self._numerator * other._numerator
            new_den = self._denominator * other._denominator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, int):
            other = Fraction(other)
        if isinstance(other, Fraction):
            new_num = self._numerator * other._denominator
            new_den = self._denominator * other._numerator
            return Fraction(new_num, new_den)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, int):
            other = Fraction(other)
        return other.__truediv__(self)

    def __neg__(self):
        return Fraction(-self._numerator, self._denominator)

    def __pos__(self):
        return Fraction(self._numerator, self._denominator)

    def __abs__(self):
        return Fraction(abs(self._numerator), self._denominator)

    def __float__(self):
        return self._numerator / self._denominator

    def __int__(self):
        if self._numerator < 0:
            return -(-self._numerator // self._denominator)
        return self._numerator // self._denominator

    def __hash__(self):
        # If this fraction equals an integer, hash like that integer
        if self._denominator == 1:
            return hash(self._numerator)
        return hash((self._numerator, self._denominator))

    def __bool__(self):
        return self._numerator != 0

    def limit_denominator(self, max_denominator=1000000):
        """Find the closest Fraction with denominator <= max_denominator."""
        if max_denominator < 1:
            raise ValueError("max_denominator must be at least 1")
        
        if self._denominator <= max_denominator:
            return Fraction(self._numerator, self._denominator)
        
        # Use the Stern-Brocot / mediants approach (continued fractions)
        # This is the standard algorithm used in CPython's fractions module
        
        # We want to find p/q closest to self._numerator/self._denominator
        # with q <= max_denominator
        
        p0, q0 = 0, 1
        p1, q1 = 1, 0
        
        n = self._numerator
        d = self._denominator
        
        # Handle negative
        negative = n < 0
        if negative:
            n = -n
        
        # Continued fraction expansion
        while True:
            a = n // d
            q2 = q0 + a * q1
            if q2 > max_denominator:
                break
            p0, q0, p1, q1 = p1, q1, p0 + a * p1, q2
            n, d = d, n - a * d
            if d == 0:
                break
        
        # At this point, p1/q1 is the last convergent within bounds
        # We need to check the best approximation
        k = (max_denominator - q0) // q1
        
        # Two candidates: p1/q1 and (p0 + k*p1)/(q0 + k*q1)
        bound1 = Fraction(p1, q1)
        bound2 = Fraction(p0 + k * p1, q0 + k * q1)
        
        target = Fraction(self._numerator, self._denominator)
        
        # Pick the closer one
        diff1 = abs(bound1 - target)
        diff2 = abs(bound2 - target)
        
        if diff1 <= diff2:
            result = bound1
        else:
            result = bound2
        
        if negative:
            return -result
        return result


def fractions2_add():
    result = Fraction(1, 2) + Fraction(1, 3)
    return result.numerator == 5 and result.denominator == 6


def fractions2_mul():
    result = Fraction(2, 3) * Fraction(3, 4)
    return result.numerator


def fractions2_limit_denom():
    result = Fraction(1, 3).limit_denominator(10)
    return result == Fraction(1, 3)