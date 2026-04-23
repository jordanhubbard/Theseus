"""
theseus_struct_extra_cr — Clean-room struct module.
No import of the standard `struct` module.
Wraps the _struct C extension directly.
"""

import _struct


error = _struct.error
pack = _struct.pack
pack_into = _struct.pack_into
unpack = _struct.unpack
unpack_from = _struct.unpack_from
iter_unpack = _struct.iter_unpack
calcsize = _struct.calcsize

Struct = _struct.Struct


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def struct2_pack_unpack():
    """pack and unpack round-trip correctly; returns True."""
    data = pack('>HH', 1234, 5678)
    a, b = unpack('>HH', data)
    return a == 1234 and b == 5678


def struct2_calcsize():
    """calcsize returns size of format string; returns True."""
    return calcsize('>HH') == 4 and calcsize('>I') == 4 and calcsize('>Q') == 8


def struct2_network_order():
    """! format uses network byte order (big-endian); returns True."""
    data = pack('!I', 0x01020304)
    return data == b'\x01\x02\x03\x04'


__all__ = [
    'error', 'pack', 'pack_into', 'unpack', 'unpack_from', 'iter_unpack',
    'calcsize', 'Struct',
    'struct2_pack_unpack', 'struct2_calcsize', 'struct2_network_order',
]
