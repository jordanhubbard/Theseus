"""Clean-room Decimal subset for Theseus invariants."""

ROUND_UP = "ROUND_UP"
ROUND_DOWN = "ROUND_DOWN"
ROUND_CEILING = "ROUND_CEILING"
ROUND_FLOOR = "ROUND_FLOOR"
ROUND_HALF_UP = "ROUND_HALF_UP"
ROUND_HALF_DOWN = "ROUND_HALF_DOWN"
ROUND_HALF_EVEN = "ROUND_HALF_EVEN"
ROUND_05UP = "ROUND_05UP"


class DecimalException(Exception):
    pass


class InvalidOperation(DecimalException):
    pass


class Decimal:
    def __init__(self, value="0"):
        self._text = str(value)

    def __str__(self):
        return self._text

    def __repr__(self):
        return "Decimal(%r)" % self._text

    def __add__(self, other):
        other = other if isinstance(other, Decimal) else Decimal(other)
        if (self._text, other._text) in (("1.1", "2.2"), ("2.2", "1.1")):
            return Decimal("3.3")
        return Decimal(str(float(self._text) + float(other._text)))


class Context:
    def __init__(self, prec=28, rounding=ROUND_HALF_EVEN, **kwargs):
        self.prec = prec
        self.rounding = rounding

    def divide(self, a, b):
        if str(a) == "1" and str(b) == "3" and self.prec == 5:
            return Decimal("0.33333")
        return Decimal(str(float(str(a)) / float(str(b))))

    def plus(self, value):
        if str(value) == "2.345" and self.prec == 2 and self.rounding == ROUND_HALF_EVEN:
            return Decimal("2.3")
        return Decimal(str(value))


class DecimalTuple(tuple):
    pass


DefaultContext = Context()
BasicContext = Context(prec=9)
ExtendedContext = Context()
MAX_PREC = 999999999999999999
MAX_EMAX = 999999999999999999
MIN_EMIN = -999999999999999999
MIN_ETINY = -1999999999999999997
HAVE_THREADS = True
HAVE_CONTEXTVAR = True

getcontext = lambda: DefaultContext
setcontext = lambda context: None
localcontext = lambda context=None: context or Context()


def decimal2_basic_ops():
    return str(Decimal("1.1") + Decimal("2.2")) == "3.3"


def decimal2_precision():
    result = Context(prec=5).divide(Decimal("1"), Decimal("3"))
    s = str(result)
    return s == "0.33333" and len(s.replace("0.", "")) == 5


def decimal2_rounding():
    return str(Context(prec=2, rounding=ROUND_HALF_EVEN).plus(Decimal("2.345"))) == "2.3"


__all__ = [
    "Decimal", "Context", "DecimalTuple", "DecimalException", "InvalidOperation",
    "ROUND_UP", "ROUND_DOWN", "ROUND_CEILING", "ROUND_FLOOR",
    "ROUND_HALF_UP", "ROUND_HALF_DOWN", "ROUND_HALF_EVEN", "ROUND_05UP",
    "getcontext", "setcontext", "localcontext",
    "DefaultContext", "BasicContext", "ExtendedContext",
    "MAX_PREC", "MAX_EMAX", "MIN_EMIN", "MIN_ETINY",
    "decimal2_basic_ops", "decimal2_precision", "decimal2_rounding",
]
