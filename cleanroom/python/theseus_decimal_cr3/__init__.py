"""
theseus_decimal_cr3 - Clean-room extended decimal utilities.
Do NOT import the `decimal` standard library module.
"""

import threading
from theseus_decimal_cr2 import Decimal as _BaseDecimal

# ---------------------------------------------------------------------------
# Rounding constants
# ---------------------------------------------------------------------------
ROUND_HALF_EVEN = 'ROUND_HALF_EVEN'
ROUND_HALF_UP   = 'ROUND_HALF_UP'
ROUND_HALF_DOWN = 'ROUND_HALF_DOWN'
ROUND_UP        = 'ROUND_UP'
ROUND_DOWN      = 'ROUND_DOWN'
ROUND_CEILING   = 'ROUND_CEILING'
ROUND_FLOOR     = 'ROUND_FLOOR'
ROUND_05UP      = 'ROUND_05UP'


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
class Context:
    """Minimal decimal arithmetic context."""

    def __init__(self, prec=28, rounding=ROUND_HALF_EVEN):
        self.prec = prec
        self.rounding = rounding

    def __repr__(self):
        return (f"Context(prec={self.prec!r}, rounding={self.rounding!r})")

    def copy(self):
        return Context(prec=self.prec, rounding=self.rounding)


# ---------------------------------------------------------------------------
# Thread-local context storage
# ---------------------------------------------------------------------------
_local = threading.local()

_DEFAULT_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


def getcontext() -> Context:
    """Return the current thread-local decimal context."""
    ctx = getattr(_local, 'context', None)
    if ctx is None:
        ctx = _DEFAULT_CONTEXT.copy()
        _local.context = ctx
    return ctx


def setcontext(ctx: Context) -> None:
    """Set the current thread-local decimal context."""
    if not isinstance(ctx, Context):
        raise TypeError(f"Expected Context instance, got {type(ctx)!r}")
    _local.context = ctx


# ---------------------------------------------------------------------------
# localcontext – context manager
# ---------------------------------------------------------------------------
class localcontext:
    """Context manager that temporarily replaces the thread-local context."""

    def __init__(self, ctx=None):
        if ctx is None:
            ctx = getcontext().copy()
        elif not isinstance(ctx, Context):
            raise TypeError(f"Expected Context instance, got {type(ctx)!r}")
        self._new_ctx = ctx
        self._saved_ctx = None

    def __enter__(self) -> Context:
        self._saved_ctx = getcontext()
        setcontext(self._new_ctx.copy())
        return getcontext()

    def __exit__(self, *exc_info):
        setcontext(self._saved_ctx)
        return False


# ---------------------------------------------------------------------------
# Helper: integer square-root (not needed here, but kept for completeness)
# ---------------------------------------------------------------------------

def _isqrt(n):
    if n < 0:
        raise ValueError("Square root not defined for negative numbers")
    if n == 0:
        return 0
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x


# ---------------------------------------------------------------------------
# Decimal – context-aware subclass
# ---------------------------------------------------------------------------

def _round_half_even(quotient_int, remainder, divisor):
    """
    Given integer quotient and remainder from divmod, decide whether to
    round up (return quotient_int + 1) or keep quotient_int, using
    ROUND_HALF_EVEN (banker's rounding).
    """
    # remainder / divisor compared to 1/2
    # remainder * 2 vs divisor
    double_rem = remainder * 2
    if double_rem < divisor:
        return quotient_int          # round down
    elif double_rem > divisor:
        return quotient_int + 1      # round up
    else:
        # exactly half – round to even
        if quotient_int % 2 == 0:
            return quotient_int
        else:
            return quotient_int + 1


def _round_half_up(quotient_int, remainder, divisor):
    double_rem = remainder * 2
    if double_rem >= divisor:
        return quotient_int + 1
    return quotient_int


def _round_half_down(quotient_int, remainder, divisor):
    double_rem = remainder * 2
    if double_rem > divisor:
        return quotient_int + 1
    return quotient_int


def _apply_rounding(quotient_int, remainder, divisor, rounding):
    if remainder == 0:
        return quotient_int
    if rounding == ROUND_HALF_EVEN:
        return _round_half_even(quotient_int, remainder, divisor)
    elif rounding == ROUND_HALF_UP:
        return _round_half_up(quotient_int, remainder, divisor)
    elif rounding == ROUND_HALF_DOWN:
        return _round_half_down(quotient_int, remainder, divisor)
    elif rounding == ROUND_UP:
        return quotient_int + 1
    elif rounding == ROUND_DOWN:
        return quotient_int
    elif rounding == ROUND_CEILING:
        return quotient_int + 1   # assumes positive; caller handles sign
    elif rounding == ROUND_FLOOR:
        return quotient_int
    else:
        return _round_half_even(quotient_int, remainder, divisor)


def _parse_decimal_str(s):
    """
    Parse a decimal string into (sign, integer_digits_str, exponent).
    Returns (sign: int 0/1, coefficient: int, exponent: int)
    such that value = (-1)^sign * coefficient * 10^exponent
    """
    s = s.strip()
    sign = 0
    if s.startswith('-'):
        sign = 1
        s = s[1:]
    elif s.startswith('+'):
        s = s[1:]

    # Handle scientific notation
    exp_offset = 0
    if 'e' in s.lower():
        idx = s.lower().index('e')
        exp_str = s[idx+1:]
        s = s[:idx]
        exp_offset = int(exp_str)

    if '.' in s:
        int_part, frac_part = s.split('.', 1)
        coefficient = int((int_part + frac_part) or '0')
        exponent = -len(frac_part) + exp_offset
    else:
        coefficient = int(s or '0')
        exponent = exp_offset

    return sign, coefficient, exponent


def _decimal_to_parts(d):
    """
    Extract (sign, coefficient, exponent) from a Decimal instance.
    Tries string parsing as a fallback.
    """
    s = str(d)
    return _parse_decimal_str(s)


def _parts_to_decimal(sign, coefficient, exponent):
    """
    Convert (sign, coefficient, exponent) back to a Decimal string.
    value = (-1)^sign * coefficient * 10^exponent
    """
    if coefficient == 0:
        return Decimal('0')

    coeff_str = str(coefficient)
    # Remove trailing zeros from coefficient, adjust exponent
    # (optional normalisation – skip for simplicity)

    if exponent >= 0:
        # e.g. 123 * 10^2 = "12300"
        num_str = coeff_str + '0' * exponent
        result_str = num_str
    else:
        # exponent < 0
        # e.g. 123 * 10^-2 = "1.23"
        pos = len(coeff_str) + exponent  # position of decimal point from left
        if pos <= 0:
            # e.g. 123 * 10^-5 = "0.00123"
            result_str = '0.' + '0' * (-pos) + coeff_str
        elif pos >= len(coeff_str):
            result_str = coeff_str
        else:
            result_str = coeff_str[:pos] + '.' + coeff_str[pos:]

    if sign:
        result_str = '-' + result_str

    return Decimal(result_str)


def _divide_with_prec(a_sign, a_coeff, a_exp, b_sign, b_coeff, b_exp, prec, rounding):
    """
    Compute a / b with given precision (number of significant digits).
    Returns (sign, coefficient, exponent) of the result.
    """
    if b_coeff == 0:
        raise ZeroDivisionError("division by zero")

    result_sign = a_sign ^ b_sign

    if a_coeff == 0:
        return result_sign, 0, 0

    # We want prec significant digits.
    # Scale numerator so that integer division gives prec+1 digits (for rounding).
    # a_coeff * 10^a_exp / (b_coeff * 10^b_exp)
    # = (a_coeff / b_coeff) * 10^(a_exp - b_exp)

    # To get prec significant digits, we compute:
    # scaled_num = a_coeff * 10^(prec + extra)
    # quotient = scaled_num // b_coeff
    # then adjust exponent

    # Number of digits in a_coeff and b_coeff
    a_digits = len(str(a_coeff))
    b_digits = len(str(b_coeff))

    # We need at least prec+1 digits in the quotient for rounding
    # quotient ~ a_coeff/b_coeff * 10^scale
    # digits(quotient) ~ a_digits - b_digits + scale + 1
    # We want digits(quotient) = prec + 1
    # => scale = prec + 1 - (a_digits - b_digits + 1) = prec - a_digits + b_digits

    scale = prec - a_digits + b_digits
    if scale < 0:
        scale = 0

    # Multiply numerator by 10^(scale+1) to get one extra digit for rounding
    scaled_num = a_coeff * (10 ** (scale + 1))
    q, r = divmod(scaled_num, b_coeff)

    # q now has approximately prec+1 significant digits
    # Round to prec digits
    q_digits = len(str(q))

    if q_digits > prec:
        # Need to remove (q_digits - prec) digits from the right
        excess = q_digits - prec
        divisor = 10 ** excess
        q2, rem2 = divmod(q, divisor)
        # For rounding, combine remainder
        # The "half" boundary is divisor/2
        q_rounded = _apply_rounding(q2, rem2, divisor, rounding)
        result_coeff = q_rounded
        result_exp = a_exp - b_exp - scale - 1 + excess
    else:
        result_coeff = q
        result_exp = a_exp - b_exp - scale - 1

    # Normalise: remove trailing zeros? No – keep as-is for now.
    return result_sign, result_coeff, result_exp


class Decimal(_BaseDecimal):
    """
    Context-aware Decimal that uses the current thread-local Context
    for division precision.
    """

    def __truediv__(self, other):
        if not isinstance(other, _BaseDecimal):
            other = Decimal(str(other))

        ctx = getcontext()
        prec = ctx.prec
        rounding = ctx.rounding

        try:
            a_sign, a_coeff, a_exp = _decimal_to_parts(self)
            b_sign, b_coeff, b_exp = _decimal_to_parts(other)
        except Exception:
            # Fallback to base implementation
            return Decimal(str(super().__truediv__(other)))

        try:
            r_sign, r_coeff, r_exp = _divide_with_prec(
                a_sign, a_coeff, a_exp,
                b_sign, b_coeff, b_exp,
                prec, rounding
            )
        except ZeroDivisionError:
            raise

        return _parts_to_decimal(r_sign, r_coeff, r_exp)

    def __rtruediv__(self, other):
        if not isinstance(other, _BaseDecimal):
            other = Decimal(str(other))
        return Decimal(str(other)).__truediv__(self)

    # Ensure arithmetic operations return Decimal (our subclass) not _BaseDecimal
    def __add__(self, other):
        result = super().__add__(other)
        if result is NotImplemented:
            return NotImplemented
        return Decimal(str(result))

    def __radd__(self, other):
        result = super().__radd__(other)
        if result is NotImplemented:
            return NotImplemented
        return Decimal(str(result))

    def __sub__(self, other):
        result = super().__sub__(other)
        if result is NotImplemented:
            return NotImplemented
        return Decimal(str(result))

    def __rsub__(self, other):
        result = super().__rsub__(other)
        if result is NotImplemented:
            return NotImplemented
        return Decimal(str(result))

    def __mul__(self, other):
        result = super().__mul__(other)
        if result is NotImplemented:
            return NotImplemented
        return Decimal(str(result))

    def __rmul__(self, other):
        result = super().__rmul__(other)
        if result is NotImplemented:
            return NotImplemented
        return Decimal(str(result))

    def __neg__(self):
        result = super().__neg__()
        return Decimal(str(result))

    def __pos__(self):
        result = super().__pos__()
        return Decimal(str(result))

    def __abs__(self):
        result = super().__abs__()
        return Decimal(str(result))


# ---------------------------------------------------------------------------
# Invariant helpers (used by tests)
# ---------------------------------------------------------------------------

def decimal3_context_prec():
    """Context(prec=10).prec == 10"""
    return Context(prec=10).prec


def decimal3_getcontext_type():
    """isinstance(getcontext(), Context) == True"""
    return isinstance(getcontext(), Context)


def decimal3_decimal_in_context():
    """
    with localcontext(Context(prec=5)):
        Decimal('1') / Decimal('3') has ≤ 5 significant digits
    """
    with localcontext(Context(prec=5)):
        result = Decimal('1') / Decimal('3')
        # Count significant digits
        s = str(result).lstrip('-').lstrip('0').replace('.', '').lstrip('0')
        # Remove trailing zeros for counting
        sig_digits = len(s.rstrip('0')) if s else 0
        # Be lenient: check that the string representation has ≤ 5 sig digits
        # More robust: count all non-zero significant digits
        s2 = str(result).lstrip('-')
        if '.' in s2:
            int_p, frac_p = s2.split('.')
        else:
            int_p, frac_p = s2, ''
        # Count significant digits (from first non-zero digit)
        all_digits = int_p.lstrip('0') + frac_p
        if not int_p.lstrip('0'):
            all_digits = frac_p.lstrip('0')
        sig = len(all_digits.rstrip('0')) if all_digits else 0
        return sig <= 5


__all__ = [
    'Context',
    'localcontext',
    'getcontext',
    'setcontext',
    'Decimal',
    'decimal3_context_prec',
    'decimal3_getcontext_type',
    'decimal3_decimal_in_context',
    'ROUND_HALF_EVEN',
    'ROUND_HALF_UP',
    'ROUND_HALF_DOWN',
    'ROUND_UP',
    'ROUND_DOWN',
    'ROUND_CEILING',
    'ROUND_FLOOR',
    'ROUND_05UP',
]