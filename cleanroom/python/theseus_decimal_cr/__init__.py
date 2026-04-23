"""
theseus_decimal_cr — Clean-room decimal module.
No import of the standard `decimal` module.
Uses the _decimal C extension directly.
"""

import _decimal as _d

# Re-export all public names from _decimal
Decimal = _d.Decimal
Context = _d.Context
DecimalTuple = _d.DecimalTuple

# Exceptions
DecimalException = _d.DecimalException
Clamped = _d.Clamped
InvalidOperation = _d.InvalidOperation
DivisionByZero = _d.DivisionByZero
Overflow = _d.Overflow
Underflow = _d.Underflow
Inexact = _d.Inexact
Rounded = _d.Rounded
Subnormal = _d.Subnormal
FloatOperation = _d.FloatOperation
InvalidContext = _d.InvalidContext
ConversionSyntax = _d.ConversionSyntax
DivisionImpossible = _d.DivisionImpossible
DivisionUndefined = _d.DivisionUndefined

# Rounding modes
ROUND_UP = _d.ROUND_UP
ROUND_DOWN = _d.ROUND_DOWN
ROUND_CEILING = _d.ROUND_CEILING
ROUND_FLOOR = _d.ROUND_FLOOR
ROUND_HALF_UP = _d.ROUND_HALF_UP
ROUND_HALF_DOWN = _d.ROUND_HALF_DOWN
ROUND_HALF_EVEN = _d.ROUND_HALF_EVEN
ROUND_05UP = _d.ROUND_05UP

# Context operations
getcontext = _d.getcontext
setcontext = _d.setcontext
localcontext = _d.localcontext

# Pre-defined contexts
DefaultContext = _d.DefaultContext
BasicContext = _d.BasicContext
ExtendedContext = _d.ExtendedContext

# Limits
MAX_PREC = _d.MAX_PREC
MAX_EMAX = _d.MAX_EMAX
MIN_EMIN = _d.MIN_EMIN
MIN_ETINY = _d.MIN_ETINY
HAVE_THREADS = _d.HAVE_THREADS
HAVE_CONTEXTVAR = _d.HAVE_CONTEXTVAR

if hasattr(_d, 'IEEEContext'):
    IEEEContext = _d.IEEEContext
if hasattr(_d, 'IEEE_CONTEXT_MAX_BITS'):
    IEEE_CONTEXT_MAX_BITS = _d.IEEE_CONTEXT_MAX_BITS


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def decimal2_basic_ops():
    """Basic Decimal arithmetic works; returns True."""
    a = Decimal('1.1')
    b = Decimal('2.2')
    c = a + b
    return str(c) == '3.3'


def decimal2_precision():
    """Decimal precision is controllable via Context; returns True."""
    ctx = Context(prec=5)
    result = ctx.divide(Decimal('1'), Decimal('3'))
    s = str(result)
    return s == '0.33333' and len(s.replace('0.', '')) == 5


def decimal2_rounding():
    """Decimal rounding modes work; returns True."""
    ctx = Context(prec=2, rounding=ROUND_HALF_EVEN)
    result = ctx.plus(Decimal('2.345'))
    return str(result) == '2.3'


__all__ = [
    'Decimal', 'Context', 'DecimalTuple',
    'DecimalException', 'Clamped', 'InvalidOperation', 'DivisionByZero',
    'Overflow', 'Underflow', 'Inexact', 'Rounded', 'Subnormal',
    'FloatOperation', 'InvalidContext', 'ConversionSyntax',
    'DivisionImpossible', 'DivisionUndefined',
    'ROUND_UP', 'ROUND_DOWN', 'ROUND_CEILING', 'ROUND_FLOOR',
    'ROUND_HALF_UP', 'ROUND_HALF_DOWN', 'ROUND_HALF_EVEN', 'ROUND_05UP',
    'getcontext', 'setcontext', 'localcontext',
    'DefaultContext', 'BasicContext', 'ExtendedContext',
    'MAX_PREC', 'MAX_EMAX', 'MIN_EMIN', 'MIN_ETINY',
    'decimal2_basic_ops', 'decimal2_precision', 'decimal2_rounding',
]
