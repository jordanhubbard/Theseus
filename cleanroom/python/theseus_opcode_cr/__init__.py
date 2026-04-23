"""
theseus_opcode_cr — Clean-room opcode module.
No import of the standard `opcode` module.
Uses _opcode and _opcode_metadata C extensions directly.
"""

import _opcode as _c_opcode
from _opcode_metadata import (
    opmap as opmap,
    _specializations,
    _specialized_opmap,
)
try:
    from _opcode_metadata import HAVE_ARGUMENT, MIN_INSTRUMENTED_OPCODE
except ImportError:
    HAVE_ARGUMENT = 90
    MIN_INSTRUMENTED_OPCODE = 0

EXTENDED_ARG = opmap.get('EXTENDED_ARG', 144)

opname = ['<%r>' % (op,) for op in range(max(opmap.values()) + 1)]
for _m in (opmap, _specialized_opmap):
    for _op, _i in _m.items():
        opname[_i] = _op

cmp_op = ('<', '<=', '==', '!=', '>', '>=')

stack_effect = _c_opcode.stack_effect

hasarg = [op for op in opmap.values() if _c_opcode.has_arg(op)]
hasconst = [op for op in opmap.values() if _c_opcode.has_const(op)]
hasname = [op for op in opmap.values() if _c_opcode.has_name(op)]
hasjump = [op for op in opmap.values() if _c_opcode.has_jump(op)]
hasjrel = hasjump
hasjabs = []
haslocal = [op for op in opmap.values() if _c_opcode.has_local(op)]
hasfree = [op for op in opmap.values() if _c_opcode.has_free(op)]
hasexc = [op for op in opmap.values() if _c_opcode.has_exc(op)]
hascompare = [op for op in opmap.values() if op in (
    opmap.get('COMPARE_OP', -1),
    opmap.get('IS_OP', -1),
    opmap.get('CONTAINS_OP', -1),
)]
hascompare = [x for x in hascompare if x >= 0]


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def opcode2_opmap():
    """opmap is a non-empty dict mapping opcode names to numbers; returns True."""
    return isinstance(opmap, dict) and len(opmap) > 0


def opcode2_opname():
    """opname is a non-empty list of opcode names; returns True."""
    return isinstance(opname, list) and len(opname) > 0


def opcode2_load_const():
    """LOAD_CONST is in opmap and opname round-trips; returns True."""
    if 'LOAD_CONST' not in opmap:
        return False
    idx = opmap['LOAD_CONST']
    return opname[idx] == 'LOAD_CONST'


__all__ = [
    'cmp_op', 'stack_effect', 'opname', 'opmap',
    'HAVE_ARGUMENT', 'EXTENDED_ARG',
    'hasarg', 'hasconst', 'hasname', 'hasjump', 'hasjrel', 'hasjabs',
    'haslocal', 'hasfree', 'hasexc', 'hascompare',
    'opcode2_opmap', 'opcode2_opname', 'opcode2_load_const',
]
