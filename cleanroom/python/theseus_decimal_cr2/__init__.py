"""
theseus_decimal_cr2 - Clean-room extended decimal arithmetic.
No import of the original 'decimal' module or any third-party library.
"""

import threading
import math as _math
import contextlib

# ---------------------------------------------------------------------------
# Rounding mode constants
# ---------------------------------------------------------------------------
ROUND_HALF_UP   = 'ROUND_HALF_UP'
ROUND_HALF_EVEN = 'ROUND_HALF_EVEN'
ROUND_DOWN      = 'ROUND_DOWN'

# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class Context:
    """Decimal arithmetic context."""

    def __init__(self, prec=28, rounding=None):
        if prec < 1:
            raise ValueError("prec must be >= 1")
        self.prec = prec
        self.rounding = rounding if rounding is not None else ROUND_HALF_EVEN

    def __repr__(self):
        return f"Context(prec={self.prec}, rounding={self.rounding!r})"

    def copy(self):
        return Context(prec=self.prec, rounding=self.rounding)


# ---------------------------------------------------------------------------
# Thread-local context storage
# ---------------------------------------------------------------------------

_local = threading.local()
_default_context = Context(prec=28, rounding=ROUND_HALF_EVEN)


def getcontext() -> Context:
    """Return the current thread's decimal context."""
    ctx = getattr(_local, 'context', None)
    if ctx is None:
        _local.context = _default_context.copy()
    return _local.context


def setcontext(ctx: Context):
    """Set the current thread's decimal context."""
    _local.context = ctx


@contextlib.contextmanager
def localcontext(ctx=None):
    """Context manager that temporarily overrides the decimal context."""
    old_ctx = getcontext().copy()
    if ctx is None:
        new_ctx = old_ctx.copy()
    else:
        new_ctx = ctx.copy()
    setcontext(new_ctx)
    try:
        yield new_ctx
    finally:
        setcontext(old_ctx)


# ---------------------------------------------------------------------------
# Internal helpers for arbitrary-precision decimal arithmetic
# ---------------------------------------------------------------------------

def _parse_decimal_string(s: str):
    """
    Parse a decimal string into (sign, integer_digits, exponent).
    sign: 0 for positive, 1 for negative
    integer_digits: integer (the coefficient without decimal point)
    exponent: integer (power of 10 to apply)
    
    e.g. '3.14'  -> (0, 314, -2)
         '-2.5'  -> (1, 25, -1)
         '1E+3'  -> (0, 1, 3)
         '0'     -> (0, 0, 0)
    """
    s = s.strip()
    sign = 0
    if s.startswith('-'):
        sign = 1
        s = s[1:]
    elif s.startswith('+'):
        s = s[1:]

    # Handle special values
    s_upper = s.upper()
    if s_upper in ('INF', 'INFINITY'):
        return (sign, 'inf', 0)
    if s_upper in ('NAN', 'SNAN'):
        return (sign, 'nan', 0)

    # Split on 'E' or 'e'
    if 'E' in s.upper():
        idx = s.upper().index('E')
        mantissa = s[:idx]
        exp_str = s[idx+1:]
        exp_extra = int(exp_str)
    else:
        mantissa = s
        exp_extra = 0

    # Split mantissa on '.'
    if '.' in mantissa:
        int_part, frac_part = mantissa.split('.', 1)
        coefficient_str = int_part + frac_part
        exponent = -len(frac_part) + exp_extra
    else:
        coefficient_str = mantissa
        exponent = exp_extra

    if not coefficient_str:
        coefficient_str = '0'

    coefficient = int(coefficient_str)
    return (sign, coefficient, exponent)


def _normalize_coefficient(coeff: int, exp: int):
    """Remove trailing zeros from coefficient, adjusting exponent."""
    if coeff == 0:
        return 0, 0
    while coeff % 10 == 0:
        coeff //= 10
        exp += 1
    return coeff, exp


def _round_coefficient(coeff: int, n_digits: int, rounding: str) -> int:
    """
    Round 'coeff' (an integer) to 'n_digits' significant digits.
    Returns the rounded integer (may have n_digits or n_digits+1 digits if carry).
    """
    if n_digits <= 0:
        raise ValueError("n_digits must be >= 1")
    
    num_digits = len(str(abs(coeff))) if coeff != 0 else 1
    
    if num_digits <= n_digits:
        return coeff  # No rounding needed
    
    # We need to drop (num_digits - n_digits) digits
    drop = num_digits - n_digits
    divisor = 10 ** drop
    
    truncated = coeff // divisor
    remainder = coeff % divisor
    
    # Half-point
    half = divisor // 2
    remainder_times2 = remainder * 2
    
    if rounding == ROUND_DOWN:
        # Truncate
        return truncated
    elif rounding == ROUND_HALF_UP:
        if remainder >= (divisor + 1) // 2:  # remainder >= ceil(divisor/2)
            # Actually: round half up means >= 0.5 rounds up
            if remainder * 2 >= divisor:
                return truncated + 1
            else:
                return truncated
        else:
            return truncated
    elif rounding == ROUND_HALF_EVEN:
        if remainder_times2 > divisor:
            return truncated + 1
        elif remainder_times2 < divisor:
            return truncated
        else:
            # Exactly half - round to even
            if truncated % 2 == 0:
                return truncated
            else:
                return truncated + 1
    else:
        # Default: ROUND_HALF_EVEN
        if remainder_times2 > divisor:
            return truncated + 1
        elif remainder_times2 < divisor:
            return truncated
        else:
            if truncated % 2 == 0:
                return truncated
            else:
                return truncated + 1


# ---------------------------------------------------------------------------
# Decimal class
# ---------------------------------------------------------------------------

class Decimal:
    """
    Arbitrary-precision decimal number.
    
    Internal representation:
      _sign: 0 (positive) or 1 (negative)
      _coeff: non-negative integer (the coefficient)
      _exp: integer exponent (value = sign * coeff * 10^exp)
      _special: None, 'inf', or 'nan'
    """

    def __init__(self, value=0):
        if isinstance(value, Decimal):
            self._sign = value._sign
            self._coeff = value._coeff
            self._exp = value._exp
            self._special = value._special
            return

        if isinstance(value, int):
            self._sign = 0 if value >= 0 else 1
            self._coeff = abs(value)
            self._exp = 0
            self._special = None
            return

        if isinstance(value, str):
            sign, coeff, exp = _parse_decimal_string(value)
            self._sign = sign
            if coeff == 'inf':
                self._special = 'inf'
                self._coeff = 0
                self._exp = 0
            elif coeff == 'nan':
                self._special = 'nan'
                self._coeff = 0
                self._exp = 0
            else:
                self._special = None
                self._coeff = coeff
                self._exp = exp
            return

        if isinstance(value, float):
            # Convert float to string first
            s = repr(value)
            self.__init__(s)
            return

        raise TypeError(f"Cannot convert {type(value)} to Decimal")

    def _is_nan(self):
        return self._special == 'nan'

    def _is_inf(self):
        return self._special == 'inf'

    def _is_special(self):
        return self._special is not None

    def _value_as_fraction(self):
        """Return (numerator, denominator) such that value = num/den."""
        if self._exp >= 0:
            return self._coeff * (10 ** self._exp), 1
        else:
            return self._coeff, 10 ** (-self._exp)

    def __repr__(self):
        return f"Decimal('{self}')"

    def __str__(self):
        if self._special == 'nan':
            return 'NaN'
        if self._special == 'inf':
            return '-Infinity' if self._sign else 'Infinity'

        sign_str = '-' if self._sign else ''
        coeff_str = str(self._coeff)
        exp = self._exp

        if exp >= 0:
            # e.g. coeff=314, exp=2 -> 31400
            result = coeff_str + '0' * exp
            return sign_str + result
        else:
            # exp < 0
            # We need to place decimal point
            n_frac = -exp  # number of fractional digits
            if len(coeff_str) > n_frac:
                int_part = coeff_str[:-n_frac]
                frac_part = coeff_str[-n_frac:]
            else:
                int_part = '0'
                frac_part = coeff_str.zfill(n_frac)
            return sign_str + int_part + '.' + frac_part

    def __eq__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        if self._is_nan() or other._is_nan():
            return False
        if self._is_inf() and other._is_inf():
            return self._sign == other._sign
        if self._is_special() or other._is_special():
            return False
        # Compare values: self._coeff * 10^self._exp == other._coeff * 10^other._exp
        # Cross multiply
        se = self._exp
        oe = other._exp
        if se == oe:
            return self._sign == other._sign and self._coeff == other._coeff
        elif se > oe:
            diff = se - oe
            return self._sign == other._sign and self._coeff * (10 ** diff) == other._coeff
        else:
            diff = oe - se
            return self._sign == other._sign and self._coeff == other._coeff * (10 ** diff)

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._compare(other) < 0

    def __le__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._compare(other) <= 0

    def __gt__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._compare(other) > 0

    def __ge__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._compare(other) >= 0

    def _compare(self, other):
        """Return negative, zero, or positive."""
        # Handle signs
        if self._sign != other._sign:
            # Different signs: negative < positive
            # But 0 == -0
            if self._coeff == 0 and other._coeff == 0:
                return 0
            return -1 if self._sign else 1

        # Same sign
        # Compare magnitudes
        mag = self._compare_magnitude(other)
        if self._sign:  # both negative
            return -mag
        return mag

    def _compare_magnitude(self, other):
        """Compare absolute values. Return -1, 0, 1."""
        # Align exponents
        se = self._exp
        oe = other._exp
        if se == oe:
            sc = self._coeff
            oc = other._coeff
        elif se > oe:
            diff = se - oe
            sc = self._coeff * (10 ** diff)
            oc = other._coeff
        else:
            diff = oe - se
            sc = self._coeff
            oc = other._coeff * (10 ** diff)

        if sc < oc:
            return -1
        elif sc > oc:
            return 1
        return 0

    def __add__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._add(other)

    def __radd__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        return other._add(self)

    def __sub__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        neg_other = Decimal(other)
        neg_other._sign = 1 - neg_other._sign if neg_other._coeff != 0 else 0
        return self._add(neg_other)

    def __rsub__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        return other._add(self.__neg__())

    def __neg__(self):
        result = Decimal(self)
        if result._coeff != 0:
            result._sign = 1 - result._sign
        return result

    def __pos__(self):
        return Decimal(self)

    def __abs__(self):
        result = Decimal(self)
        result._sign = 0
        return result

    def _add(self, other):
        """Add two Decimal values."""
        if self._is_nan() or other._is_nan():
            return _make_nan()
        if self._is_inf() and other._is_inf():
            if self._sign == other._sign:
                return _make_inf(self._sign)
            return _make_nan()  # inf - inf = NaN
        if self._is_inf():
            return _make_inf(self._sign)
        if other._is_inf():
            return _make_inf(other._sign)

        # Align exponents
        se = self._exp
        oe = other._exp

        if se == oe:
            sc = self._coeff
            oc = other._coeff
            exp = se
        elif se > oe:
            diff = se - oe
            sc = self._coeff * (10 ** diff)
            oc = other._coeff
            exp = oe
        else:
            diff = oe - se
            sc = self._coeff
            oc = other._coeff * (10 ** diff)
            exp = se

        # Now add with signs
        if self._sign == other._sign:
            result_coeff = sc + oc
            result_sign = self._sign
        else:
            if sc >= oc:
                result_coeff = sc - oc
                result_sign = self._sign
            else:
                result_coeff = oc - sc
                result_sign = other._sign

        if result_coeff == 0:
            result_sign = 0

        result = Decimal.__new__(Decimal)
        result._sign = result_sign
        result._coeff = result_coeff
        result._exp = exp
        result._special = None
        return result

    def __mul__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._mul(other)

    def __rmul__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        return other._mul(self)

    def _mul(self, other):
        if self._is_nan() or other._is_nan():
            return _make_nan()
        if self._is_inf() or other._is_inf():
            if self._coeff == 0 or other._coeff == 0:
                return _make_nan()
            return _make_inf(self._sign ^ other._sign)

        result_sign = self._sign ^ other._sign
        result_coeff = self._coeff * other._coeff
        result_exp = self._exp + other._exp

        if result_coeff == 0:
            result_sign = 0

        result = Decimal.__new__(Decimal)
        result._sign = result_sign
        result._coeff = result_coeff
        result._exp = result_exp
        result._special = None
        return result

    def __truediv__(self, other):
        if isinstance(other, int):
            other = Decimal(other)
        if not isinstance(other, Decimal):
            return NotImplemented
        return self._div(other)

    def _div(self, other):
        ctx = getcontext()
        prec = ctx.prec
        rounding = ctx.rounding

        if self._is_nan() or other._is_nan():
            return _make_nan()
        if other._coeff == 0 and not other._is_inf():
            if self._coeff == 0:
                return _make_nan()
            return _make_inf(self._sign ^ other._sign)
        if self._is_inf() and other._is_inf():
            return _make_nan()
        if self._is_inf():
            return _make_inf(self._sign ^ other._sign)
        if other._is_inf():
            result = Decimal.__new__(Decimal)
            result._sign = self._sign ^ other._sign
            result._coeff = 0
            result._exp = 0
            result._special = None
            return result

        # Perform division to 'prec' significant digits
        # value = self._coeff * 10^self._exp / (other._coeff * 10^other._exp)
        # = (self._coeff / other._coeff) * 10^(self._exp - other._exp)

        # Scale numerator to get enough digits
        num = self._coeff
        den = other._coeff
        exp = self._exp - other._exp

        # We want prec+2 digits of quotient for rounding
        target_digits = prec + 2
        num_digits_num = len(str(num)) if num > 0 else 1
        num_digits_den = len(str(den)) if den > 0 else 1

        # Scale num up
        scale = target_digits - num_digits_num + num_digits_den
        if scale > 0:
            num = num * (10 ** scale)
            exp -= scale

        quotient = num // den
        remainder = num % den

        # Round
        result_sign = self._sign ^ other._sign
        # Apply rounding based on remainder
        # remainder/den compared to 0.5
        remainder2 = remainder * 2
        if rounding == ROUND_DOWN:
            pass  # truncate
        elif rounding == ROUND_HALF_UP:
            if remainder2 >= den:
                quotient += 1
        elif rounding == ROUND_HALF_EVEN:
            if remainder2 > den:
                quotient += 1
            elif remainder2 == den:
                if quotient % 2 == 1:
                    quotient += 1
        else:
            if remainder2 >= den:
                quotient += 1

        # Trim to prec digits
        q_str = str(quotient)
        if len(q_str) > prec:
            excess = len(q_str) - prec
            quotient = _round_coefficient(quotient, prec, rounding)
            exp += excess

        if quotient == 0:
            result_sign = 0

        result = Decimal.__new__(Decimal)
        result._sign = result_sign
        result._coeff = quotient
        result._exp = exp
        result._special = None
        return result

    def quantize(self, exp_decimal, rounding=None):
        """
        Return a value equal to self rounded to the same number of decimal
        places as exp_decimal.
        
        exp_decimal: a Decimal whose exponent determines the target scale.
        rounding: rounding mode (defaults to context rounding).
        """
        if rounding is None:
            rounding = getcontext().rounding

        if self._is_nan() or exp_decimal._is_nan():
            return _make_nan()
        if self._is_inf():
            return _make_inf(self._sign)

        target_exp = exp_decimal._exp
        # We want to round self to have exponent = target_exp

        current_exp = self._exp
        current_coeff = self._coeff

        if current_exp == target_exp:
            # Already at the right scale, but may need to round to context prec
            result = Decimal.__new__(Decimal)
            result._sign = self._sign
            result._coeff = current_coeff
            result._exp = current_exp
            result._special = None
            return result

        elif current_exp > target_exp:
            # Need more decimal places: multiply coefficient
            diff = current_exp - target_exp
            new_coeff = current_coeff * (10 ** diff)
            result = Decimal.__new__(Decimal)
            result._sign = self._sign
            result._coeff = new_coeff
            result._exp = target_exp
            result._special = None
            return result

        else:
            # current_exp < target_exp: need to reduce decimal places (round)
            diff = target_exp - current_exp
            # We need to divide current_coeff by 10^diff with rounding
            divisor = 10 ** diff
            truncated = current_coeff // divisor
            remainder = current_coeff % divisor

            # Apply rounding
            remainder2 = remainder * 2
            if rounding == ROUND_DOWN:
                new_coeff = truncated
            elif rounding == ROUND_HALF_UP:
                if remainder2 >= divisor:
                    new_coeff = truncated + 1
                else:
                    new_coeff = truncated
            elif rounding == ROUND_HALF_EVEN:
                if remainder2 > divisor:
                    new_coeff = truncated + 1
                elif remainder2 < divisor:
                    new_coeff = truncated
                else:
                    # Exactly half
                    if truncated % 2 == 0:
                        new_coeff = truncated
                    else:
                        new_coeff = truncated + 1
            else:
                # Default ROUND_HALF_EVEN
                if remainder2 > divisor:
                    new_coeff = truncated + 1
                elif remainder2 < divisor:
                    new_coeff = truncated
                else:
                    if truncated % 2 == 0:
                        new_coeff = truncated
                    else:
                        new_coeff = truncated + 1

            result_sign = self._sign
            if new_coeff == 0:
                result_sign = 0

            result = Decimal.__new__(Decimal)
            result._sign = result_sign
            result._coeff = new_coeff
            result._exp = target_exp
            result._special = None
            return result

    def __int__(self):
        if self._is_special():
            raise ValueError("Cannot convert special Decimal to int")
        # Truncate toward zero
        if self._exp >= 0:
            val = self._coeff * (10 ** self._exp)
        else:
            val = self._coeff // (10 ** (-self._exp))
        return -val if self._sign else val

    def __float__(self):
        if self._special == 'nan':
            return float('nan')
        if self._special == 'inf':
            return float('-inf') if self._sign else float('inf')
        val = self._coeff * (10.0 ** self._exp)
        return -val if self._sign else val

    def __bool__(self):
        if self._is_special():
            return True
        return self._coeff != 0

    def __hash__(self):
        # Hash based on numeric value
        if self._is_nan():
            return hash('nan')
        if self._is_inf():
            return hash(float('-inf') if self._sign else float('inf'))
        # Normalize
        c, e = _normalize_coefficient(self._coeff, self._exp)
        return hash((self._sign, c, e))


def _make_nan():
    result = Decimal.__new__(Decimal)
    result._sign = 0
    result._coeff = 0
    result._exp = 0
    result._special = 'nan'
    return result


def _make_inf(sign=0):
    result = Decimal.__new__(Decimal)
    result._sign = sign
    result._coeff = 1  # non-zero to indicate infinity
    result._exp = 0
    result._special = 'inf'
    return result


# ---------------------------------------------------------------------------
# Verification functions (as described in the spec)
# ---------------------------------------------------------------------------

def decimal2_getcontext_prec():
    """Returns True if getcontext().prec >= 1."""
    return getcontext().prec >= 1


def decimal2_round_half_up():
    """Returns Decimal('2.5').quantize(Decimal('1'), ROUND_HALF_UP)."""
    return Decimal('2.5').quantize(Decimal('1'), ROUND_HALF_UP)


def decimal2_round_half_even():
    """Returns Decimal('2.5').quantize(Decimal('1'), ROUND_HALF_EVEN)."""
    return Decimal('2.5').quantize(Decimal('1'), ROUND_HALF_EVEN)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    'getcontext',
    'setcontext',
    'localcontext',
    'Context',
    'Decimal',
    'ROUND_HALF_UP',
    'ROUND_HALF_EVEN',
    'ROUND_DOWN',
    'decimal2_getcontext_prec',
    'decimal2_round_half_up',
    'decimal2_round_half_even',
]