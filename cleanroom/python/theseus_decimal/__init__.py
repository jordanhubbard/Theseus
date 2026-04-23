"""
theseus_decimal — clean-room fixed-precision decimal arithmetic.
No import of the standard `decimal` or `fractions` modules.
"""

import math as _math
import re as _re

__all__ = ["Decimal", "ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN", "ROUND_UP"]

# Rounding modes
ROUND_HALF_UP   = "ROUND_HALF_UP"
ROUND_HALF_EVEN = "ROUND_HALF_EVEN"
ROUND_DOWN      = "ROUND_DOWN"
ROUND_UP        = "ROUND_UP"

_DEFAULT_PRECISION = 28  # digits after decimal point for division


def _gcd(a, b):
    """Euclidean GCD for non-negative integers."""
    while b:
        a, b = b, a % b
    return a


def _isqrt(n):
    """Integer square root (Python 3.8+ has math.isqrt, but let's be safe)."""
    if n < 0:
        raise ValueError("Square root of negative number")
    if n == 0:
        return 0
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x


class Decimal:
    """
    Fixed-precision decimal number.

    Internally stored as:
        value = _coeff * 10^(-_scale)
    where _coeff is a Python int (may be negative) and _scale >= 0.
    """

    __slots__ = ("_coeff", "_scale", "_negative_zero")

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, value=0, _coeff=None, _scale=None):
        """
        Decimal(int_or_str)
        Decimal('1.23')  → coeff=123, scale=2
        Decimal('0.10')  → coeff=10,  scale=2
        Decimal(5)       → coeff=5,   scale=0
        """
        if _coeff is not None and _scale is not None:
            # Internal fast path
            self._coeff = int(_coeff)
            self._scale = int(_scale)
            self._negative_zero = False
            return

        self._negative_zero = False

        if isinstance(value, Decimal):
            self._coeff = value._coeff
            self._scale = value._scale
            return

        if isinstance(value, int):
            self._coeff = value
            self._scale = 0
            return

        if isinstance(value, float):
            # Convert float via string representation
            s = repr(value)
            return self.__init__(s)

        if isinstance(value, str):
            s = value.strip()
            if not s:
                raise ValueError("Cannot convert empty string to Decimal")

            # Handle sign
            negative = False
            if s[0] == '-':
                negative = True
                s = s[1:]
            elif s[0] == '+':
                s = s[1:]

            # Handle scientific notation
            exp_match = _re.match(
                r'^(\d+)(?:\.(\d*))?[eE]([+-]?\d+)$', s
            )
            if exp_match:
                int_part = exp_match.group(1)
                frac_part = exp_match.group(2) or ''
                exponent = int(exp_match.group(3))
                digits = int_part + frac_part
                scale = len(frac_part) - exponent
                if scale < 0:
                    digits = digits + '0' * (-scale)
                    scale = 0
                coeff = int(digits)
                if negative:
                    coeff = -coeff
                self._coeff = coeff
                self._scale = scale
                return

            # Normal decimal notation
            match = _re.match(r'^(\d+)(?:\.(\d*))?$', s)
            if not match:
                raise ValueError(f"Cannot convert {value!r} to Decimal")

            int_part  = match.group(1)
            frac_part = match.group(2) if match.group(2) is not None else ''

            coeff = int(int_part + frac_part)
            scale = len(frac_part)

            if negative:
                coeff = -coeff

            self._coeff = coeff
            self._scale = scale
            return

        raise TypeError(f"Cannot convert {type(value).__name__!r} to Decimal")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _from_parts(cls, coeff, scale):
        obj = object.__new__(cls)
        obj._coeff = int(coeff)
        obj._scale = int(scale)
        obj._negative_zero = False
        return obj

    def _align(self, other):
        """Return (coeff_self, coeff_other, common_scale) with same scale."""
        if self._scale == other._scale:
            return self._coeff, other._coeff, self._scale
        elif self._scale > other._scale:
            diff = self._scale - other._scale
            return self._coeff, other._coeff * (10 ** diff), self._scale
        else:
            diff = other._scale - self._scale
            return self._coeff * (10 ** diff), other._coeff, other._scale

    # ------------------------------------------------------------------
    # String / repr
    # ------------------------------------------------------------------

    def __str__(self):
        coeff = self._coeff
        scale = self._scale

        negative = coeff < 0
        coeff_abs = abs(coeff)

        digits = str(coeff_abs)

        if scale == 0:
            result = digits
        elif scale >= len(digits):
            # Need leading zeros after decimal point
            result = '0.' + '0' * (scale - len(digits)) + digits
        else:
            insert = len(digits) - scale
            result = digits[:insert] + '.' + digits[insert:]

        if negative:
            result = '-' + result

        return result

    def __repr__(self):
        return f"Decimal('{self}')"

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, _ = self._align(other)
        return a == b

    def __lt__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, _ = self._align(other)
        return a < b

    def __le__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, _ = self._align(other)
        return a <= b

    def __gt__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, _ = self._align(other)
        return a > b

    def __ge__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, _ = self._align(other)
        return a >= b

    def __hash__(self):
        # Normalize: remove trailing zeros from scale
        coeff, scale = self._coeff, self._scale
        while scale > 0 and coeff % 10 == 0:
            coeff //= 10
            scale -= 1
        return hash((coeff, scale))

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def __neg__(self):
        return Decimal._from_parts(-self._coeff, self._scale)

    def __pos__(self):
        return Decimal._from_parts(self._coeff, self._scale)

    def __abs__(self):
        return Decimal._from_parts(abs(self._coeff), self._scale)

    def __add__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, scale = self._align(other)
        return Decimal._from_parts(a + b, scale)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        a, b, scale = self._align(other)
        return Decimal._from_parts(a - b, scale)

    def __rsub__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return other.__sub__(self)

    def __mul__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        coeff = self._coeff * other._coeff
        scale = self._scale + other._scale
        return Decimal._from_parts(coeff, scale)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other, precision=None):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        if other._coeff == 0:
            raise ZeroDivisionError("Division by zero")

        if precision is None:
            precision = _DEFAULT_PRECISION

        # We want: self / other = (self._coeff / other._coeff) * 10^(other._scale - self._scale)
        # Result scale = precision
        # result_coeff = round(self._coeff * 10^(precision + other._scale - self._scale) / other._coeff)

        exp_adjust = precision + other._scale - self._scale

        if exp_adjust >= 0:
            numerator = self._coeff * (10 ** exp_adjust)
        else:
            # exp_adjust is negative, divide numerator
            numerator = self._coeff // (10 ** (-exp_adjust))

        # Integer division with rounding (ROUND_HALF_UP)
        denominator = other._coeff

        # We need to handle signs carefully
        neg = (numerator < 0) != (denominator < 0)
        num_abs = abs(numerator)
        den_abs = abs(denominator)

        q, r = divmod(num_abs, den_abs)

        # Round half up
        if 2 * r >= den_abs:
            q += 1

        coeff = -q if neg else q
        return Decimal._from_parts(coeff, precision)

    def __rtruediv__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return other.__truediv__(self)

    def __floordiv__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        result = self.__truediv__(other, precision=0)
        # Floor toward negative infinity
        return result

    def __mod__(self, other):
        if isinstance(other, (int, float, str)):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        # a mod b = a - (a // b) * b
        q = self.__floordiv__(other)
        return self - q * other

    def __pow__(self, other):
        if isinstance(other, int):
            if other == 0:
                return Decimal._from_parts(1, 0)
            if other > 0:
                result = Decimal._from_parts(1, 0)
                base = self
                exp = other
                while exp > 0:
                    if exp % 2 == 1:
                        result = result * base
                    base = base * base
                    exp //= 2
                return result
            else:
                # Negative exponent: 1 / self^(-other)
                pos = self.__pow__(-other)
                return Decimal._from_parts(1, 0).__truediv__(pos)
        if isinstance(other, Decimal):
            # Only support integer Decimal exponents for now
            if other._scale == 0:
                return self.__pow__(other._coeff)
            # For non-integer, convert to float (best effort)
            raise TypeError("Non-integer Decimal exponents not supported")
        return NotImplemented

    # ------------------------------------------------------------------
    # Quantize
    # ------------------------------------------------------------------

    def quantize(self, places, rounding=ROUND_HALF_UP):
        """
        Round self to the given number of decimal places.

        `places` can be:
          - an int: number of decimal places
          - a str like '0.01': number of decimal places = len of fractional part
          - a Decimal like Decimal('0.01'): same
        """
        if isinstance(places, str):
            # e.g. '0.01' → 2 decimal places
            if '.' in places:
                target_scale = len(places.split('.')[1])
            else:
                target_scale = 0
        elif isinstance(places, Decimal):
            s = str(places)
            if '.' in s:
                target_scale = len(s.split('.')[1])
            else:
                target_scale = 0
        elif isinstance(places, int):
            target_scale = places
        else:
            raise TypeError(f"Unsupported type for places: {type(places)}")

        return self._round_to_scale(target_scale, rounding)

    def _round_to_scale(self, target_scale, rounding=ROUND_HALF_UP):
        """Round self to target_scale decimal places."""
        current_scale = self._scale
        coeff = self._coeff

        if current_scale == target_scale:
            return Decimal._from_parts(coeff, target_scale)

        if current_scale < target_scale:
            # Extend scale (add trailing zeros)
            diff = target_scale - current_scale
            return Decimal._from_parts(coeff * (10 ** diff), target_scale)

        # current_scale > target_scale: need to round
        diff = current_scale - target_scale
        divisor = 10 ** diff

        negative = coeff < 0
        coeff_abs = abs(coeff)

        q, r = divmod(coeff_abs, divisor)

        if rounding == ROUND_HALF_UP:
            # Round half away from zero
            if 2 * r >= divisor:
                q += 1
        elif rounding == ROUND_HALF_EVEN:
            mid = divisor // 2
            if r > mid:
                q += 1
            elif r == mid:
                # Round to even
                if q % 2 == 1:
                    q += 1
            # else r < mid: truncate
        elif rounding == ROUND_DOWN:
            pass  # truncate toward zero
        elif rounding == ROUND_UP:
            # Round away from zero
            if r != 0:
                q += 1
        else:
            raise ValueError(f"Unknown rounding mode: {rounding}")

        result_coeff = -q if negative else q
        return Decimal._from_parts(result_coeff, target_scale)

    # ------------------------------------------------------------------
    # Type conversions
    # ------------------------------------------------------------------

    def __int__(self):
        return self._coeff // (10 ** self._scale)

    def __float__(self):
        return float(str(self))

    def __bool__(self):
        return self._coeff != 0

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_zero(self):
        return self._coeff == 0

    def sign(self):
        if self._coeff > 0:
            return 1
        if self._coeff < 0:
            return -1
        return 0

    def normalize(self):
        """Remove trailing zeros from the coefficient."""
        coeff, scale = self._coeff, self._scale
        while scale > 0 and coeff % 10 == 0:
            coeff //= 10
            scale -= 1
        return Decimal._from_parts(coeff, scale)

    def copy(self):
        return Decimal._from_parts(self._coeff, self._scale)


# ------------------------------------------------------------------
# Module-level invariant functions (as required by the spec)
# ------------------------------------------------------------------

def decimal_add_exact():
    """Decimal('0.1') + Decimal('0.2') == Decimal('0.3')"""
    return Decimal('0.1') + Decimal('0.2') == Decimal('0.3')


def decimal_str_repr():
    """str(Decimal('1.23')) == '1.23'"""
    return str(Decimal('1.23'))


def decimal_compare_equal():
    """Decimal('1.0') == Decimal('1.00')"""
    return Decimal('1.0') == Decimal('1.00')