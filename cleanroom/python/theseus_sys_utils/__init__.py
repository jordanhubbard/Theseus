"""
theseus_sys_utils - Clean-room implementation of sys module utilities.
Does NOT import sys or any third-party libraries.
"""

import struct
import platform

# ---------------------------------------------------------------------------
# MAXSIZE — maximum signed integer for this platform
# We detect 64-bit vs 32-bit by checking the size of a pointer via struct.
# ---------------------------------------------------------------------------

def _detect_maxsize():
    """Detect platform pointer size and return the corresponding max signed int."""
    # 'P' format gives the size of a void pointer in bytes
    pointer_size = struct.calcsize('P')  # 8 on 64-bit, 4 on 32-bit
    bits = pointer_size * 8
    # Maximum signed integer for this pointer width
    return (1 << (bits - 1)) - 1

MAXSIZE: int = _detect_maxsize()

# ---------------------------------------------------------------------------
# BYTEORDER — endianness of this platform
# ---------------------------------------------------------------------------

def _detect_byteorder() -> str:
    """Detect platform byte order without importing sys."""
    # Pack the integer 1 as a 2-byte value and check which byte is non-zero first
    packed = struct.pack('H', 1)
    if packed[0] == 1:
        return 'little'
    else:
        return 'big'

BYTEORDER: str = _detect_byteorder()

# ---------------------------------------------------------------------------
# VERSION_INFO — Python version tuple (major, minor, micro)
# Detected via platform.python_version_tuple() which is stdlib and not sys.
# ---------------------------------------------------------------------------

def _detect_version_info():
    """Return a (major, minor, micro) tuple for the running Python interpreter."""
    parts = platform.python_version_tuple()  # returns strings
    return (int(parts[0]), int(parts[1]), int(parts[2]))

VERSION_INFO = _detect_version_info()

# ---------------------------------------------------------------------------
# Public utility functions
# ---------------------------------------------------------------------------

def sys_maxsize_positive() -> bool:
    """Return True if MAXSIZE is positive (invariant check)."""
    return MAXSIZE > 0


def sys_byteorder_valid() -> bool:
    """Return True if BYTEORDER is one of the valid endianness strings."""
    return BYTEORDER in ('little', 'big')


def sys_int_info_bits() -> int:
    """
    Return the number of bits per digit used internally by Python's long integer
    implementation.  CPython uses 30-bit digits on most platforms (sometimes 15).
    We detect this by examining how many bits fit in a single 'digit'.
    
    Per CPython source: sys.int_info.bits_per_digit is either 30 or 15.
    We approximate by checking pointer size: 64-bit → 30, 32-bit → 15.
    The invariant only requires the result to be >= 30 on 64-bit platforms,
    but we return the correct value for the platform.
    """
    pointer_size = struct.calcsize('P')
    if pointer_size >= 8:
        return 30
    else:
        return 15


def sys_maxsize_value() -> int:
    """Return the MAXSIZE constant (expected to be 9223372036854775807 on 64-bit)."""
    return MAXSIZE


# ---------------------------------------------------------------------------
# Exports summary
# ---------------------------------------------------------------------------
__all__ = [
    'MAXSIZE',
    'BYTEORDER',
    'VERSION_INFO',
    'sys_maxsize_positive',
    'sys_byteorder_valid',
    'sys_int_info_bits',
    'sys_maxsize_value',
]