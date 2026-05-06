"""Clean-room Decimal subset for Theseus invariants.

Implements arbitrary-precision decimal arithmetic from scratch using
(sign, integer coefficient, exponent) triples. Does not import the
standard `decimal` module or any third-party library.
"""

# ---- Rounding mode constants -------------------------------------------------

ROUND_UP = "ROUND_UP"
ROUND_DOWN = "ROUND_DOWN"
ROUND_CEILING = "ROUND_CEILING"
ROUND_FLOOR = "ROUND_FLOOR"
ROUND_HALF_UP = "ROUND_HALF_UP"
ROUND_HALF_DOWN = "ROUND_HALF_DOWN"
ROUND_HALF_EVEN = "ROUND_HALF_EVEN"
ROUND_05UP = "ROUND_05UP"


# ---- Exceptions --------------------------------------------------------------

class DecimalException(Exception):
    pass


class InvalidOperation(DecimalException):
    pass


class DivisionByZero(DecimalException):
    pass


# ---- Decimal -----------------------------------------------------------------

class Decimal:
    """Arbitrary-precision decimal value held as (sign, coefficient, exponent).

    Numeric value = (-1)**sign * coefficient * 10**exponent
    """

    __slots__ = ("_sign", "_coeff", "_exp")

    def __init__(self, value="0"):
        if isinstance(value, Decimal):
            self._sign = value._sign
            self._coeff = value._coeff
            self._exp = value._exp
            return
        if isinstance(value, int):
            self._sign = 1 if value < 0 else 0
            self._coeff = -value if value < 0 else value
            self._exp = 0
            return
        if isinstance(value, tuple) and len(value) == 3:
            sign, digits, exp = value
            if not isinstance(digits, tuple):
                raise InvalidOperation("digits must be a tuple")
            coeff = 0
            for d in digits:
                coeff = coeff * 10 + int(d)
            self._sign = 1 if sign else 0
            self._coeff = coeff
            self._exp = int(exp)
            return

        s = str(value).strip()
        if not s:
            raise InvalidOperation("empty string")

        sign = 0
        if s[0] == "-":
            sign = 1
            s = s[1:]
        elif s[0] == "+":
            s = s[1:]

        # Optional exponent part
        e_idx = -1
        for i, ch in enumerate(s):
            if ch == "e" or ch == "E":
                e_idx = i
                break
        if e_idx >= 0:
            mantissa = s[:e_idx]
            try:
                exp_part = int(s[e_idx + 1:])
            except ValueError:
                raise InvalidOperation("invalid exponent: %r" % value)
        else:
            mantissa = s
            exp_part = 0

        if "." in mantissa:
            int_str, _, frac_str = mantissa.partition(".")
            digits = (int_str + frac_str) or "0"
            exp = exp_part - len(frac_str)
        else:
            digits = mantissa or "0"
            exp = exp_part

        if not digits or any(c not in "0123456789" for c in digits):
            raise InvalidOperation("invalid literal: %r" % value)

        self._sign = sign
        self._coeff = int(digits)
        self._exp = exp

    # ---- string conversion ---------------------------------------------------

    def __str__(self):
        sign = "-" if self._sign else ""
        if self._coeff == 0:
            if self._exp >= 0:
                return sign + "0"
            else:
                return sign + "0." + "0" * (-self._exp)

        digits = str(self._coeff)
        if self._exp == 0:
            return sign + digits
        if self._exp > 0:
            return sign + digits + "0" * self._exp

        # exp < 0
        n_frac = -self._exp
        if n_frac < len(digits):
            return sign + digits[:-n_frac] + "." + digits[-n_frac:]
        else:
            return sign + "0." + "0" * (n_frac - len(digits)) + digits

    def __repr__(self):
        return "Decimal('%s')" % str(self)

    # ---- comparison helpers --------------------------------------------------

    def _signed_coeff(self):
        return -self._coeff if self._sign else self._coeff

    def __eq__(self, other):
        if not isinstance(other, Decimal):
            try:
                other = Decimal(other)
            except Exception:
                return NotImplemented
        # Align exponents
        a, b = self, other
        if a._exp == b._exp:
            return a._signed_coeff() == b._signed_coeff()
        if a._exp > b._exp:
            shift = a._exp - b._exp
            return a._signed_coeff() * (10 ** shift) == b._signed_coeff()
        else:
            shift = b._exp - a._exp
            return a._signed_coeff() == b._signed_coeff() * (10 ** shift)

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash((self._sign, self._coeff, self._exp))

    def __bool__(self):
        return self._coeff != 0

    # ---- arithmetic ----------------------------------------------------------

    @staticmethod
    def _from_parts(sign, coeff, exp):
        d = Decimal.__new__(Decimal)
        if coeff < 0:
            coeff = -coeff
            sign = 1 - sign
        d._sign = 1 if sign else 0
        d._coeff = coeff
        d._exp = exp
        return d

    def __add__(self, other):
        if not isinstance(other, Decimal):
            try:
                other = Decimal(other)
            except Exception:
                return NotImplemented

        if self._exp == other._exp:
            exp = self._exp
            a = self._signed_coeff()
            b = other._signed_coeff()
        elif self._exp > other._exp:
            shift = self._exp - other._exp
            a = self._signed_coeff() * (10 ** shift)
            b = other._signed_coeff()
            exp = other._exp
        else:
            shift = other._exp - self._exp
            a = self._signed_coeff()
            b = other._signed_coeff() * (10 ** shift)
            exp = self._exp

        result = a + b
        sign = 1 if result < 0 else 0
        return Decimal._from_parts(sign, abs(result), exp)

    def __radd__(self, other):
        return self.__add__(other)

    def __neg__(self):
        return Decimal._from_parts(1 - self._sign, self._coeff, self._exp)

    def __pos__(self):
        return Decimal._from_parts(self._sign, self._coeff, self._exp)

    def __sub__(self, other):
        if not isinstance(other, Decimal):
            try:
                other = Decimal(other)
            except Exception:
                return NotImplemented
        return self.__add__(-other)

    def __rsub__(self, other):
        if not isinstance(other, Decimal):
            try:
                other = Decimal(other)
            except Exception:
                return NotImplemented
        return other.__add__(-self)

    def __mul__(self, other):
        if not isinstance(other, Decimal):
            try:
                other = Decimal(other)
            except Exception:
                return NotImplemented
        sign = self._sign ^ other._sign
        coeff = self._coeff * other._coeff
        exp = self._exp + other._exp
        return Decimal._from_parts(sign, coeff, exp)

    def __rmul__(self, other):
        return self.__mul__(other)


# ---- Helpers -----------------------------------------------------------------

def _round_to_precision(value, prec, rounding):
    """Round a Decimal to `prec` significant digits using `rounding` mode."""
    if value._coeff == 0 or prec <= 0:
        return Decimal._from_parts(value._sign, value._coeff, value._exp)

    s = str(value._coeff)
    n = len(s)
    if n <= prec:
        return Decimal._from_parts(value._sign, value._coeff, value._exp)

    drop = n - prec
    keep = s[:prec]
    rest = s[prec:]
    first_drop = int(rest[0])
    remainder_nonzero = any(c != "0" for c in rest[1:])

    sign = value._sign

    if rounding == ROUND_DOWN:
        round_up = False
    elif rounding == ROUND_UP:
        round_up = first_drop != 0 or remainder_nonzero
    elif rounding == ROUND_CEILING:
        round_up = (not sign) and (first_drop != 0 or remainder_nonzero)
    elif rounding == ROUND_FLOOR:
        round_up = bool(sign) and (first_drop != 0 or remainder_nonzero)
    elif rounding == ROUND_HALF_UP:
        round_up = first_drop >= 5
    elif rounding == ROUND_HALF_DOWN:
        if first_drop > 5:
            round_up = True
        elif first_drop < 5:
            round_up = False
        else:
            round_up = remainder_nonzero
    elif rounding == ROUND_HALF_EVEN:
        if first_drop > 5:
            round_up = True
        elif first_drop < 5:
            round_up = False
        else:
            if remainder_nonzero:
                round_up = True
            else:
                # Exactly half: round to even
                round_up = (int(keep[-1]) % 2) == 1
    elif rounding == ROUND_05UP:
        last = int(keep[-1])
        if first_drop != 0 or remainder_nonzero:
            round_up = (last == 0 or last == 5)
        else:
            round_up = False
    else:
        raise InvalidOperation("unknown rounding mode: %r" % rounding)

    new_coeff = int(keep)
    new_exp = value._exp + drop
    if round_up:
        new_coeff += 1
        # Carry propagation: if 999 + 1 = 1000, drop one more digit
        if len(str(new_coeff)) > len(keep):
            new_coeff //= 10
            new_exp += 1

    return Decimal._from_parts(sign, new_coeff, new_exp)


# ---- Context -----------------------------------------------------------------

class Context:
    """Arithmetic context: precision and rounding mode."""

    def __init__(self, prec=28, rounding=ROUND_HALF_EVEN, Emin=-999999999,
                 Emax=999999999, capitals=1, clamp=0, flags=None, traps=None):
        self.prec = prec
        self.rounding = rounding
        self.Emin = Emin
        self.Emax = Emax
        self.capitals = capitals
        self.clamp = clamp
        self.flags = dict(flags) if flags else {}
        self.traps = dict(traps) if traps else {}

    def copy(self):
        return Context(prec=self.prec, rounding=self.rounding,
                       Emin=self.Emin, Emax=self.Emax,
                       capitals=self.capitals, clamp=self.clamp,
                       flags=self.flags, traps=self.traps)

    def __repr__(self):
        return ("Context(prec=%d, rounding=%s)"
                % (self.prec, self.rounding))

    # ---- operations ------------------------------------------------------

    def plus(self, value):
        """Apply context (precision + rounding) to value, no operand change."""
        if not isinstance(value, Decimal):
            value = Decimal(value)
        return _round_to_precision(value, self.prec, self.rounding)

    def minus(self, value):
        if not isinstance(value, Decimal):
            value = Decimal(value)
        return _round_to_precision(-value, self.prec, self.rounding)

    def add(self, a, b):
        if not isinstance(a, Decimal):
            a = Decimal(a)
        if not isinstance(b, Decimal):
            b = Decimal(b)
        return _round_to_precision(a + b, self.prec, self.rounding)

    def subtract(self, a, b):
        if not isinstance(a, Decimal):
            a = Decimal(a)
        if not isinstance(b, Decimal):
            b = Decimal(b)
        return _round_to_precision(a - b, self.prec, self.rounding)

    def multiply(self, a, b):
        if not isinstance(a, Decimal):
            a = Decimal(a)
        if not isinstance(b, Decimal):
            b = Decimal(b)
        return _round_to_precision(a * b, self.prec, self.rounding)

    def divide(self, a, b):
        """Return a/b rounded to self.prec significant digits."""
        if not isinstance(a, Decimal):
            a = Decimal(a)
        if not isinstance(b, Decimal):
            b = Decimal(b)
        if b._coeff == 0:
            raise DivisionByZero("division by zero")

        sign = a._sign ^ b._sign
        if a._coeff == 0:
            return Decimal._from_parts(sign, 0, a._exp - b._exp)

        num = a._coeff
        den = b._coeff
        exp_diff = a._exp - b._exp

        # Normalise so the very first integer-divide produces a non-zero
        # leading digit. We keep `scale` as the number of times we multiplied
        # the numerator by 10 before division (negative offset to exponent).
        scale = 0
        while num < den:
            num *= 10
            scale -= 1

        # Compute prec significant digits of the quotient. We compute one
        # extra "guard" digit so that we can apply the context's rounding
        # mode correctly to the final digit.
        guard = self.prec + 1
        digits = []
        for _ in range(guard):
            q, num = divmod(num, den)
            digits.append(q)
            num *= 10

        # `digits` may have a multi-digit first element if the magnitudes line
        # up so that the integer quotient was, e.g., 12 rather than a single
        # digit. After our `while num < den` loop the first quotient is in
        # range [1, 9], but be defensive anyway.
        coeff = 0
        for d in digits:
            coeff = coeff * 10 + d
        # Exponent of the constructed coefficient:
        #   value = (num/den) * 10**exp_diff
        #   we shifted num by 10**(-scale), so quotient_value = coeff * 10**(scale - (guard - 1))
        # Combined exponent for `coeff`:
        exp = exp_diff + scale - (guard - 1)

        # Detect exactness: if remainder is zero now, the unrounded value
        # is exactly representable in `guard` digits.
        unrounded = Decimal._from_parts(sign, coeff, exp)
        rounded = _round_to_precision(unrounded, self.prec, self.rounding)
        return rounded


# ---- DecimalTuple (compat) ---------------------------------------------------

class DecimalTuple(tuple):
    """Lightweight stand-in for decimal.DecimalTuple."""

    def __new__(cls, sign=0, digits=(), exponent=0):
        return tuple.__new__(cls, (sign, tuple(digits), exponent))

    @property
    def sign(self):
        return self[0]

    @property
    def digits(self):
        return self[1]

    @property
    def exponent(self):
        return self[2]


# ---- Module-level context plumbing ------------------------------------------

DefaultContext = Context()
BasicContext = Context(prec=9, rounding=ROUND_HALF_UP)
ExtendedContext = Context(prec=9, rounding=ROUND_HALF_EVEN)

MAX_PREC = 999999999999999999
MAX_EMAX = 999999999999999999
MIN_EMIN = -999999999999999999
MIN_ETINY = -1999999999999999997
HAVE_THREADS = True
HAVE_CONTEXTVAR = True

_current_context = DefaultContext


def getcontext():
    return _current_context


def setcontext(context):
    global _current_context
    _current_context = context


class _LocalContextManager:
    def __init__(self, ctx=None):
        self._ctx = ctx
        self._saved = None

    def __enter__(self):
        global _current_context
        self._saved = _current_context
        _current_context = self._ctx.copy() if self._ctx else _current_context.copy()
        return _current_context

    def __exit__(self, exc_type, exc, tb):
        global _current_context
        _current_context = self._saved
        return False


def localcontext(ctx=None):
    return _LocalContextManager(ctx)


# ---- Invariants --------------------------------------------------------------

def decimal2_basic_ops():
    return str(Decimal("1.1") + Decimal("2.2")) == "3.3"


def decimal2_precision():
    result = Context(prec=5).divide(Decimal("1"), Decimal("3"))
    s = str(result)
    return s == "0.33333" and len(s.replace("0.", "")) == 5


def decimal2_rounding():
    return str(Context(prec=2, rounding=ROUND_HALF_EVEN).plus(Decimal("2.345"))) == "2.3"


__all__ = [
    "Decimal", "Context", "DecimalTuple",
    "DecimalException", "InvalidOperation", "DivisionByZero",
    "ROUND_UP", "ROUND_DOWN", "ROUND_CEILING", "ROUND_FLOOR",
    "ROUND_HALF_UP", "ROUND_HALF_DOWN", "ROUND_HALF_EVEN", "ROUND_05UP",
    "getcontext", "setcontext", "localcontext",
    "DefaultContext", "BasicContext", "ExtendedContext",
    "MAX_PREC", "MAX_EMAX", "MIN_EMIN", "MIN_ETINY",
    "HAVE_THREADS", "HAVE_CONTEXTVAR",
    "decimal2_basic_ops", "decimal2_precision", "decimal2_rounding",
]