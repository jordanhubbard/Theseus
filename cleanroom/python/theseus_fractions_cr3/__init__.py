"""
theseus_fractions_cr3 - Clean-room implementation of extended fractions utilities.
No import of the 'fractions' module or any third-party library.
"""

import math


def _gcd(a, b):
    """Compute greatest common divisor using Euclidean algorithm."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a if a != 0 else 1


def _float_to_rational(f):
    """
    Convert a float to an exact rational (numerator, denominator) pair
    using the float's binary representation via continued fractions / 
    the float's inherent exact rational value.
    
    A float is a binary fraction: mantissa * 2^exponent.
    We use float.as_integer_ratio() equivalent logic manually.
    """
    # Handle special cases
    if f == 0.0:
        return (0, 1)
    
    # Use the fact that floats are IEEE 754 binary fractions
    # We can extract the exact rational via the following approach:
    # f = m * 2^e where m is an integer and e is an integer exponent
    # This gives us the exact rational representation
    
    import struct
    
    # Pack float as 8 bytes (double precision)
    packed = struct.pack('>d', f)
    bits = int.from_bytes(packed, 'big')
    
    sign = -1 if (bits >> 63) else 1
    exponent = (bits >> 52) & 0x7FF
    mantissa = bits & 0x000FFFFFFFFFFFFF
    
    if exponent == 0x7FF:
        raise ValueError("Cannot convert inf or nan to Fraction")
    
    if exponent == 0:
        # Subnormal number
        # value = sign * mantissa * 2^(-1022 - 52)
        numerator = sign * mantissa
        denominator = 2 ** (1022 + 52)
    else:
        # Normal number
        # value = sign * (1 + mantissa/2^52) * 2^(exponent - 1023)
        # = sign * (2^52 + mantissa) * 2^(exponent - 1023 - 52)
        m = (1 << 52) | mantissa
        e = exponent - 1023 - 52
        numerator = sign * m
        if e >= 0:
            numerator = numerator * (2 ** e)
            denominator = 1
        else:
            denominator = 2 ** (-e)
    
    g = _gcd(abs(numerator), denominator)
    return (numerator // g, denominator // g)


class Fraction:
    """
    Exact rational number implementation.
    Supports creation from (numerator, denominator) or from a float.
    """
    
    def __init__(self, numerator_or_float, denominator=None):
        if denominator is None:
            # Single argument: must be a float (or int)
            if isinstance(numerator_or_float, float):
                n, d = _float_to_rational(numerator_or_float)
            elif isinstance(numerator_or_float, int):
                n, d = numerator_or_float, 1
            elif isinstance(numerator_or_float, Fraction):
                n, d = numerator_or_float.numerator, numerator_or_float.denominator
            else:
                raise TypeError(f"Cannot create Fraction from {type(numerator_or_float)}")
        else:
            # Two arguments: numerator and denominator
            if not isinstance(numerator_or_float, int) or not isinstance(denominator, int):
                raise TypeError("Numerator and denominator must be integers")
            n, d = numerator_or_float, denominator
        
        if d == 0:
            raise ZeroDivisionError("Fraction denominator cannot be zero")
        
        # Normalize sign: denominator is always positive
        if d < 0:
            n, d = -n, -d
        
        # Simplify
        g = _gcd(abs(n), d)
        self.numerator = n // g
        self.denominator = d // g
    
    def __str__(self):
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"
    
    def __repr__(self):
        return f"Fraction({self.numerator}, {self.denominator})"
    
    def __eq__(self, other):
        if isinstance(other, Fraction):
            return self.numerator == other.numerator and self.denominator == other.denominator
        if isinstance(other, int):
            return self.denominator == 1 and self.numerator == other
        return NotImplemented
    
    def __add__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            n = self.numerator * other.denominator + other.numerator * self.denominator
            d = self.denominator * other.denominator
            return Fraction(n, d)
        return NotImplemented
    
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            n = self.numerator * other.denominator - other.numerator * self.denominator
            d = self.denominator * other.denominator
            return Fraction(n, d)
        return NotImplemented
    
    def __rsub__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            return other.__sub__(self)
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            n = self.numerator * other.numerator
            d = self.denominator * other.denominator
            return Fraction(n, d)
        return NotImplemented
    
    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __truediv__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            n = self.numerator * other.denominator
            d = self.denominator * other.numerator
            return Fraction(n, d)
        return NotImplemented
    
    def __rtruediv__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            return other.__truediv__(self)
        return NotImplemented
    
    def __neg__(self):
        return Fraction(-self.numerator, self.denominator)
    
    def __pos__(self):
        return Fraction(self.numerator, self.denominator)
    
    def __abs__(self):
        return Fraction(abs(self.numerator), self.denominator)
    
    def __float__(self):
        return self.numerator / self.denominator
    
    def __int__(self):
        return self.numerator // self.denominator
    
    def __hash__(self):
        return hash((self.numerator, self.denominator))
    
    def __lt__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            return self.numerator * other.denominator < other.numerator * self.denominator
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            return self.numerator * other.denominator <= other.numerator * self.denominator
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            return self.numerator * other.denominator > other.numerator * self.denominator
        return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, int):
            other = Fraction(other, 1)
        if isinstance(other, Fraction):
            return self.numerator * other.denominator >= other.numerator * self.denominator
        return NotImplemented


# Zero-argument invariant functions

def fractions3_from_float():
    """Returns str(Fraction(0.5)) which should be '1/2'."""
    return str(Fraction(0.5))


def fractions3_str():
    """Returns str(Fraction(3, 4)) which should be '3/4'."""
    return str(Fraction(3, 4))


def fractions3_sub():
    """Returns whether Fraction(3,4) - Fraction(1,4) == Fraction(1,2)."""
    result = Fraction(3, 4) - Fraction(1, 4)
    return result == Fraction(1, 2)