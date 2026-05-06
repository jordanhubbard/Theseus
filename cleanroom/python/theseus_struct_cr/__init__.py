"""Clean-room implementation of a struct-like module.

Implements pack/unpack/calcsize without importing the original `struct` module.
Format strings follow the conventional grammar:

    [byte_order] (count? code)*

byte_order: '<' little-endian, '>' big-endian, '!' network (big-endian),
            '=' native (treated as little-endian here, no alignment),
            '@' native default (treated as little-endian here, no alignment).

Supported codes: x c b B ? h H i I l L q Q f d e s p
(no native alignment is performed; sizes are the "standard" sizes).
"""

import math as _math


# ---------------------------------------------------------------------------
# Format parsing
# ---------------------------------------------------------------------------

_SCALAR_SIZES = {
    'x': 1, 'c': 1, 'b': 1, 'B': 1, '?': 1,
    'h': 2, 'H': 2,
    'i': 4, 'I': 4, 'l': 4, 'L': 4,
    'q': 8, 'Q': 8,
    'e': 2, 'f': 4, 'd': 8,
}

_BYTE_ORDER_CHARS = ('<', '>', '!', '=', '@')


def _parse_format(fmt):
    """Return (little_endian: bool, items: list[(count, code)])."""
    if isinstance(fmt, (bytes, bytearray)):
        fmt = fmt.decode('ascii')
    if not isinstance(fmt, str):
        raise TypeError("Struct format must be a str or bytes-like object")

    little_endian = True  # default for '@', '=', '<'
    i = 0
    n = len(fmt)
    if n > 0 and fmt[0] in _BYTE_ORDER_CHARS:
        bo = fmt[0]
        if bo in ('>', '!'):
            little_endian = False
        else:
            little_endian = True
        i = 1

    items = []
    count_str = ''
    while i < n:
        c = fmt[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            count_str += c
            i += 1
            continue
        if c in _BYTE_ORDER_CHARS:
            raise ValueError("byte order char must be at start of format")
        count = int(count_str) if count_str else 1
        count_str = ''
        if c not in _SCALAR_SIZES and c not in ('s', 'p'):
            raise ValueError("bad char in struct format: %r" % c)
        items.append((count, c))
        i += 1
    if count_str:
        raise ValueError("repeat count given without format specifier")
    return little_endian, items


# ---------------------------------------------------------------------------
# Integer encoding
# ---------------------------------------------------------------------------

def _pack_int(value, size, signed, little_endian):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise TypeError("required argument is not an integer")
    bits = size * 8
    if signed:
        lo = -(1 << (bits - 1))
        hi = (1 << (bits - 1))
        if not (lo <= value < hi):
            raise OverflowError(
                "integer %d out of range for %d-byte signed field" % (value, size))
        if value < 0:
            value += (1 << bits)
    else:
        if not (0 <= value < (1 << bits)):
            raise OverflowError(
                "integer %d out of range for %d-byte unsigned field" % (value, size))
    out = bytearray(size)
    for j in range(size):
        out[j] = value & 0xff
        value >>= 8
    if not little_endian:
        out.reverse()
    return bytes(out)


def _unpack_int(data, size, signed, little_endian):
    if len(data) != size:
        raise ValueError("buffer size mismatch in _unpack_int")
    val = 0
    if little_endian:
        for j in range(size - 1, -1, -1):
            val = (val << 8) | data[j]
    else:
        for j in range(size):
            val = (val << 8) | data[j]
    if signed and val >= (1 << (size * 8 - 1)):
        val -= (1 << (size * 8))
    return val


# ---------------------------------------------------------------------------
# IEEE 754 float encoding
# ---------------------------------------------------------------------------

def _float_to_bits(value, mantissa_bits, exponent_bits):
    """Convert a Python float to its IEEE 754 bit pattern as an int."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise TypeError("required argument is not a float")

    sign_shift = exponent_bits + mantissa_bits
    bias = (1 << (exponent_bits - 1)) - 1
    max_exp = (1 << exponent_bits) - 1

    # Determine sign — preserve negative zero
    if _math.copysign(1.0, value) < 0:
        sign_bit = 1
        value = -value
    else:
        sign_bit = 0

    # NaN
    if value != value:
        # Quiet NaN: top mantissa bit set
        return ((sign_bit << sign_shift)
                | (max_exp << mantissa_bits)
                | (1 << (mantissa_bits - 1)))

    # Infinity
    if value == float('inf'):
        return (sign_bit << sign_shift) | (max_exp << mantissa_bits)

    # Zero (after taking absolute value)
    if value == 0.0:
        return sign_bit << sign_shift

    # value > 0 here, finite, non-NaN
    m, e = _math.frexp(value)        # value = m * 2**e, 0.5 <= m < 1
    # Re-express as (1 + frac) * 2**(exp_unbiased) with frac in [0, 1).
    # Equivalent: m_norm = m * 2 in [1, 2), exp_unbiased = e - 1
    exp_field = (e - 1) + bias

    if exp_field >= max_exp:
        # Overflow to infinity
        return (sign_bit << sign_shift) | (max_exp << mantissa_bits)

    if exp_field <= 0:
        # Subnormal range. Encode as: value = mantissa * 2**(1 - bias - mantissa_bits)
        # => mantissa = value * 2**(mantissa_bits + bias - 1)
        # Using m, e:    mantissa = m * 2**(e + mantissa_bits + bias - 1)
        shift = e + mantissa_bits + bias - 1
        if shift < -1:
            # Far below smallest subnormal — rounds to zero
            return sign_bit << sign_shift
        # Use exact float scaling then round-half-to-even via Python's round()
        scaled = m * (2.0 ** shift)
        mantissa = int(round(scaled))
        if mantissa >= (1 << mantissa_bits):
            # Rounded up into the smallest normal number
            return ((sign_bit << sign_shift)
                    | (1 << mantissa_bits))
        return (sign_bit << sign_shift) | mantissa

    # Normal number
    # frac = (m * 2 - 1), in [0, 1); mantissa_field = round(frac * 2**mantissa_bits)
    frac_scaled = (m * 2.0 - 1.0) * (1 << mantissa_bits)
    mantissa_field = int(round(frac_scaled))
    if mantissa_field >= (1 << mantissa_bits):
        # Carry into exponent
        mantissa_field = 0
        exp_field += 1
        if exp_field >= max_exp:
            return (sign_bit << sign_shift) | (max_exp << mantissa_bits)
    return ((sign_bit << sign_shift)
            | (exp_field << mantissa_bits)
            | mantissa_field)


def _bits_to_float(bits, mantissa_bits, exponent_bits):
    """Convert an IEEE 754 bit pattern (int) back to a Python float."""
    sign_shift = exponent_bits + mantissa_bits
    max_exp = (1 << exponent_bits) - 1
    bias = (1 << (exponent_bits - 1)) - 1
    mantissa_mask = (1 << mantissa_bits) - 1

    sign = (bits >> sign_shift) & 1
    exp = (bits >> mantissa_bits) & max_exp
    mantissa = bits & mantissa_mask

    if exp == max_exp:
        if mantissa == 0:
            return float('-inf') if sign else float('inf')
        return float('nan')

    if exp == 0:
        if mantissa == 0:
            return -0.0 if sign else 0.0
        # Subnormal
        value = mantissa * (2.0 ** (1 - bias - mantissa_bits))
    else:
        # Normal — use ldexp for precision
        frac = 1.0 + mantissa / float(1 << mantissa_bits)
        value = _math.ldexp(frac, exp - bias)

    return -value if sign else value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _calcsize_impl(fmt=''):
    """Return the number of bytes that pack/unpack will use for fmt."""
    _, items = _parse_format(fmt)
    total = 0
    for count, code in items:
        if code in ('s', 'p'):
            total += count
        else:
            total += count * _SCALAR_SIZES[code]
    return total


def _pack_impl(fmt='', *args):
    """Pack values according to the format string."""
    little_endian, items = _parse_format(fmt)

    # Validate arg count first
    expected_args = 0
    for count, code in items:
        if code == 'x':
            continue
        if code in ('s', 'p'):
            expected_args += 1
        else:
            expected_args += count
    if len(args) != expected_args:
        raise ValueError(
            "pack expected %d items for packing (got %d)"
            % (expected_args, len(args)))

    out = bytearray()
    arg_idx = 0

    for count, code in items:
        if code == 'x':
            out.extend(b'\x00' * count)
            continue

        if code == 's':
            data = args[arg_idx]
            arg_idx += 1
            if isinstance(data, str):
                data = data.encode('latin-1')
            elif isinstance(data, bytearray):
                data = bytes(data)
            elif not isinstance(data, (bytes, memoryview)):
                raise TypeError("argument for 's' must be bytes or str")
            data = bytes(data)
            if len(data) >= count:
                out.extend(data[:count])
            else:
                out.extend(data)
                out.extend(b'\x00' * (count - len(data)))
            continue

        if code == 'p':
            data = args[arg_idx]
            arg_idx += 1
            if isinstance(data, str):
                data = data.encode('latin-1')
            elif isinstance(data, bytearray):
                data = bytes(data)
            elif not isinstance(data, (bytes, memoryview)):
                raise TypeError("argument for 'p' must be bytes or str")
            data = bytes(data)
            if count == 0:
                continue
            n_bytes = min(len(data), count - 1, 255)
            out.append(n_bytes)
            out.extend(data[:n_bytes])
            pad = count - 1 - n_bytes
            if pad > 0:
                out.extend(b'\x00' * pad)
            continue

        for _ in range(count):
            value = args[arg_idx]
            arg_idx += 1

            if code == 'c':
                if isinstance(value, str):
                    value = value.encode('latin-1')
                if not isinstance(value, (bytes, bytearray)) or len(value) != 1:
                    raise TypeError("char format requires a bytes object of length 1")
                out.append(value[0])
            elif code == 'b':
                out.extend(_pack_int(value, 1, True, little_endian))
            elif code == 'B':
                out.extend(_pack_int(value, 1, False, little_endian))
            elif code == '?':
                out.append(1 if value else 0)
            elif code == 'h':
                out.extend(_pack_int(value, 2, True, little_endian))
            elif code == 'H':
                out.extend(_pack_int(value, 2, False, little_endian))
            elif code in ('i', 'l'):
                out.extend(_pack_int(value, 4, True, little_endian))
            elif code in ('I', 'L'):
                out.extend(_pack_int(value, 4, False, little_endian))
            elif code == 'q':
                out.extend(_pack_int(value, 8, True, little_endian))
            elif code == 'Q':
                out.extend(_pack_int(value, 8, False, little_endian))
            elif code == 'e':
                bits = _float_to_bits(value, 10, 5)
                out.extend(_pack_int(bits, 2, False, little_endian))
            elif code == 'f':
                bits = _float_to_bits(value, 23, 8)
                out.extend(_pack_int(bits, 4, False, little_endian))
            elif code == 'd':
                bits = _float_to_bits(value, 52, 11)
                out.extend(_pack_int(bits, 8, False, little_endian))
            else:
                raise ValueError("bad char in struct format: %r" % code)

    return bytes(out)


def _unpack_impl(fmt='', buffer=b''):
    """Unpack the buffer according to fmt, returning a tuple of values."""
    little_endian, items = _parse_format(fmt)

    if isinstance(buffer, memoryview):
        buf = bytes(buffer)
    elif isinstance(buffer, (bytes, bytearray)):
        buf = bytes(buffer)
    else:
        raise TypeError("a bytes-like object is required")

    expected = _calcsize_impl(fmt)
    if len(buf) != expected:
        raise ValueError(
            "unpack requires a buffer of %d bytes (got %d)"
            % (expected, len(buf)))

    result = []
    pos = 0

    for count, code in items:
        if code == 'x':
            pos += count
            continue

        if code == 's':
            result.append(buf[pos:pos + count])
            pos += count
            continue

        if code == 'p':
            if count == 0:
                continue
            n_bytes = buf[pos]
            n_bytes = min(n_bytes, count - 1)
            result.append(buf[pos + 1:pos + 1 + n_bytes])
            pos += count
            continue

        for _ in range(count):
            if code == 'c':
                result.append(buf[pos:pos + 1])
                pos += 1
            elif code == 'b':
                result.append(_unpack_int(buf[pos:pos + 1], 1, True, little_endian))
                pos += 1
            elif code == 'B':
                result.append(_unpack_int(buf[pos:pos + 1], 1, False, little_endian))
                pos += 1
            elif code == '?':
                result.append(buf[pos] != 0)
                pos += 1
            elif code == 'h':
                result.append(_unpack_int(buf[pos:pos + 2], 2, True, little_endian))
                pos += 2
            elif code == 'H':
                result.append(_unpack_int(buf[pos:pos + 2], 2, False, little_endian))
                pos += 2
            elif code in ('i', 'l'):
                result.append(_unpack_int(buf[pos:pos + 4], 4, True, little_endian))
                pos += 4
            elif code in ('I', 'L'):
                result.append(_unpack_int(buf[pos:pos + 4], 4, False, little_endian))
                pos += 4
            elif code == 'q':
                result.append(_unpack_int(buf[pos:pos + 8], 8, True, little_endian))
                pos += 8
            elif code == 'Q':
                result.append(_unpack_int(buf[pos:pos + 8], 8, False, little_endian))
                pos += 8
            elif code == 'e':
                bits = _unpack_int(buf[pos:pos + 2], 2, False, little_endian)
                result.append(_bits_to_float(bits, 10, 5))
                pos += 2
            elif code == 'f':
                bits = _unpack_int(buf[pos:pos + 4], 4, False, little_endian)
                result.append(_bits_to_float(bits, 23, 8))
                pos += 4
            elif code == 'd':
                bits = _unpack_int(buf[pos:pos + 8], 8, False, little_endian)
                result.append(_bits_to_float(bits, 52, 11))
                pos += 8
            else:
                raise ValueError("bad char in struct format: %r" % code)

    return tuple(result)


pack = _pack_impl
unpack = _unpack_impl
calcsize = _calcsize_impl


def struct2_pack():
    return pack('>H', 258) == b'\x01\x02'


def struct2_unpack():
    return unpack('>H', b'\x01\x02') == (258,)


def struct2_calcsize():
    return calcsize('>HI') == 6


__all__ = ['pack', 'unpack', 'calcsize', 'struct2_pack', 'struct2_unpack', 'struct2_calcsize']
