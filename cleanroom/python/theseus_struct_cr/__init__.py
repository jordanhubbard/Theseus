"""
theseus_struct_cr — Clean-room struct module.
No import of the standard `struct` module.
Uses the _struct C extension directly.
"""

import _struct as _s

# Re-export everything from _struct
pack = _s.pack
unpack = _s.unpack
pack_into = _s.pack_into
unpack_from = _s.unpack_from
iter_unpack = _s.iter_unpack
calcsize = _s.calcsize
Struct = _s.Struct
error = _s.error


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def struct2_pack():
    """pack() encodes values to bytes; returns True."""
    data = pack('>HI', 0x1234, 0xDEADBEEF)
    return data == b'\x12\x34\xDE\xAD\xBE\xEF'


def struct2_unpack():
    """unpack() decodes bytes to values; returns True."""
    data = b'\x12\x34\xDE\xAD\xBE\xEF'
    result = unpack('>HI', data)
    return result == (0x1234, 0xDEADBEEF)


def struct2_calcsize():
    """calcsize() returns correct byte counts; returns True."""
    return (calcsize('B') == 1 and
            calcsize('H') == 2 and
            calcsize('I') == 4 and
            calcsize('Q') == 8 and
            calcsize('4s') == 4)


__all__ = [
    'pack', 'unpack', 'pack_into', 'unpack_from', 'iter_unpack',
    'calcsize', 'Struct', 'error',
    'struct2_pack', 'struct2_unpack', 'struct2_calcsize',
]
