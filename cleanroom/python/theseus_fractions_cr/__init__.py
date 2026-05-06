"""Clean-room implementation of a Fraction (rational number) type.

No imports from the standard ``fractions`` module are used; the GCD and
arithmetic are implemented from scratch.
"""


def _gcd(a, b):
    """Greatest common divisor (non-negative)."""
    a = -a if a < 0 else a
    b = -b if b < 0 else b
    while b:
        a, b = b, a % b
    return a


class Fraction(object):
    """A rational number stored in lowest terms with positive denominator."""

    __slots__ = ("_n", "_d")

    def __init__(self, numerator=0, denominator=1):
        if isinstance(numerator, Fraction) and denominator == 1:
            self._n = numerator._n
            self._d = numerator._d
            return

        if not isinstance(numerator, int) or isinstance(numerator, bool):
            if isinstance(numerator, bool):
                numerator = int(numerator)
            else:
                raise TypeError("numerator must be an int")
        if not isinstance(denominator, int) or isinstance(denominator, bool):
            if isinstance(denominator, bool):
                denominator = int(denominator)
            else:
                raise TypeError("denominator must be an int")

        if denominator == 0:
            raise ZeroDivisionError("Fraction with denominator zero")

        if denominator < 0:
            numerator = -numerator
            denominator = -denominator

        g = _gcd(numerator, denominator)
        if g > 1:
            numerator //= g
            denominator //= g

        self._n = numerator
        self._d = denominator

    # ----- accessors -----

    @property
    def numerator(self):
        return self._n

    @property
    def denominator(self):
        return self._d

    # ----- representation -----

    def __repr__(self):
        return "Fraction(%d, %d)" % (self._n, self._d)

    def __str__(self):
        if self._d == 1:
            return str(self._n)
        return "%d/%d" % (self._n, self._d)

    # ----- helpers -----

    @staticmethod
    def _coerce(other):
        if isinstance(other, Fraction):
            return other
        if isinstance(other, int) and not isinstance(other, bool):
            return Fraction(other, 1)
        return None

    # ----- arithmetic -----

    def __add__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(self._n * o._d + o._n * self._d, self._d * o._d)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(self._n * o._d - o._n * self._d, self._d * o._d)

    def __rsub__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(o._n * self._d - self._n * o._d, self._d * o._d)

    def __mul__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return Fraction(self._n * o._n, self._d * o._d)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        if o._n == 0:
            raise ZeroDivisionError("Fraction division by zero")
        return Fraction(self._n * o._d, self._d * o._n)

    def __rtruediv__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        if self._n == 0:
            raise ZeroDivisionError("Fraction division by zero")
        return Fraction(o._n * self._d, o._d * self._n)

    def __neg__(self):
        return Fraction(-self._n, self._d)

    def __pos__(self):
        return Fraction(self._n, self._d)

    def __abs__(self):
        return Fraction(-self._n if self._n < 0 else self._n, self._d)

    # ----- comparison -----

    def _cmp_key(self):
        return (self._n, self._d)

    def __eq__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n == o._n and self._d == o._d

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d < o._n * self._d

    def __le__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d <= o._n * self._d

    def __gt__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d > o._n * self._d

    def __ge__(self, other):
        o = self._coerce(other)
        if o is None:
            return NotImplemented
        return self._n * o._d >= o._n * self._d

    def __hash__(self):
        return hash((self._n, self._d))

    def __bool__(self):
        return self._n != 0

    # ----- conversions -----

    def __int__(self):
        if self._n < 0:
            return -((-self._n) // self._d)
        return self._n // self._d

    def __float__(self):
        return self._n / self._d


# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------


def fractions2_create():
    """Constructing a Fraction stores numerator/denominator in lowest terms."""
    f = Fraction(3, 4)
    if f.numerator != 3 or f.denominator != 4:
        return False
    if str(f) != "3/4":
        return False

    # Default denominator is 1.
    g = Fraction(7)
    if g.numerator != 7 or g.denominator != 1:
        return False

    # Denominator zero is rejected.
    try:
        Fraction(1, 0)
    except ZeroDivisionError:
        pass
    else:
        return False

    # Negative denominator is normalized so the denominator is positive.
    h = Fraction(1, -2)
    if h.numerator != -1 or h.denominator != 2:
        return False

    return True


def fractions2_add():
    """Addition of two fractions yields a reduced fraction."""
    if Fraction(1, 2) + Fraction(1, 3) != Fraction(5, 6):
        return False
    if Fraction(1, 4) + Fraction(1, 4) != Fraction(1, 2):
        return False
    if Fraction(2, 3) + Fraction(1, 3) != Fraction(1, 1):
        return False
    # Adding an int.
    if Fraction(1, 2) + 1 != Fraction(3, 2):
        return False
    if 1 + Fraction(1, 2) != Fraction(3, 2):
        return False
    # Negative addition.
    if Fraction(1, 2) + Fraction(-1, 2) != Fraction(0, 1):
        return False
    return True


def fractions2_reduce():
    """Fractions are stored in lowest terms with positive denominator."""
    f = Fraction(6, 8)
    if f.numerator != 3 or f.denominator != 4:
        return False

    g = Fraction(100, 25)
    if g.numerator != 4 or g.denominator != 1:
        return False

    h = Fraction(-9, 12)
    if h.numerator != -3 or h.denominator != 4:
        return False

    # Reduction also applies to arithmetic results.
    p = Fraction(2, 4) * Fraction(2, 4)
    if p.numerator != 1 or p.denominator != 4:
        return False

    return True