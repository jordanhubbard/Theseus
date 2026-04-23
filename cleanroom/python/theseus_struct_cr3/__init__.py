"""
theseus_struct_cr3 - Clean-room struct utilities implementation.
No import of the 'struct' module allowed.
"""

import sys
import math

# ---------------------------------------------------------------------------
# Format character sizes (in bytes)
# ---------------------------------------------------------------------------

_FMT_SIZES = {
    'x': 1,  # pad byte
    'c': 1,  # char
    'b': 1,  # signed byte
    'B': 1,  # unsigned byte
    '?': 1,  # bool
    'h': 2,  # signed short
    'H': 2,  # unsigned short
    'i': 4,  # signed int
    'I': 4,  # unsigned int
    'l': 4,  # signed long
    'L': 4,  # unsigned long
    'q': 8,  # signed long long
    'Q': 8,  # unsigned long long
    'f': 4,  # float
    'd': 8,  # double
    's': 1,  # char[] (count is number of bytes)
    'p': 1,  # pascal string (count includes length byte)
}

_BYTE_ORDER_CHARS = '<>=!'

# ---------------------------------------------------------------------------
# Format string parser
# ---------------------------------------------------------------------------

def _parse_fmt(fmt):
    """
    Parse a format string into (byte_order, [(count, char), ...]).
    Returns byte_order as one of '<', '>', '=', '!' (default '=').
    Each item is (count, fmt_char).
    """
    if not fmt:
        return '=', []

    idx = 0
    if fmt[0] in _BYTE_ORDER_CHARS:
        byte_order = fmt[0]
        idx = 1
    else:
        byte_order = '='

    items = []
    n = len(fmt)
    while idx < n:
        # Collect digits for count
        count_str = ''
        while idx < n and fmt[idx].isdigit():
            count_str += fmt[idx]
            idx += 1
        if idx >= n:
            break
        ch = fmt[idx]
        idx += 1
        count = int(count_str) if count_str else 1
        if ch not in _FMT_SIZES:
            raise ValueError(f"Unknown format character: {ch!r}")
        items.append((count, ch))

    return byte_order, items


# ---------------------------------------------------------------------------
# calcsize
# ---------------------------------------------------------------------------

def calcsize(fmt):
    """Return the number of bytes required by the format string."""
    _, items = _parse_fmt(fmt)
    total = 0
    for count, ch in items:
        if ch == 's':
            # count bytes total for the string
            total += count
        elif ch == 'p':
            # pascal string: count bytes total (first byte is length)
            total += count
        else:
            total += _FMT_SIZES[ch] * count
    return total


# ---------------------------------------------------------------------------
# Integer encoding helpers
# ---------------------------------------------------------------------------

def _int_to_bytes(value, size, signed, big_endian):
    """Convert an integer to bytes."""
    if signed:
        if value < -(1 << (size * 8 - 1)) or value >= (1 << (size * 8 - 1)):
            raise ValueError(f"Value {value} out of range for signed {size}-byte integer")
        if value < 0:
            value = value + (1 << (size * 8))
    else:
        if value < 0 or value >= (1 << (size * 8)):
            raise ValueError(f"Value {value} out of range for unsigned {size}-byte integer")

    result = []
    for _ in range(size):
        result.append(value & 0xFF)
        value >>= 8

    if big_endian:
        result.reverse()
    return bytes(result)


def _bytes_to_int(data, signed, big_endian):
    """Convert bytes to an integer."""
    if big_endian:
        data = bytes(reversed(data))
    value = 0
    for i, b in enumerate(data):
        value |= b << (8 * i)
    if signed:
        size = len(data)
        if value >= (1 << (size * 8 - 1)):
            value -= (1 << (size * 8))
    return value


# ---------------------------------------------------------------------------
# Float encoding helpers (IEEE 754)
# ---------------------------------------------------------------------------

def _float_to_bytes_32(value, big_endian):
    """Pack a Python float into 4 bytes (IEEE 754 single precision)."""
    if math.isnan(value):
        # Canonical NaN
        bits = 0x7FC00000
    elif math.isinf(value):
        if value > 0:
            bits = 0x7F800000
        else:
            bits = 0xFF800000
    elif value == 0.0:
        # Handle -0.0
        import math as _math
        if _math.copysign(1.0, value) < 0:
            bits = 0x80000000
        else:
            bits = 0x00000000
    else:
        sign = 0
        if value < 0:
            sign = 1
            value = -value
        exp = math.floor(math.log2(value))
        # Normalize
        mantissa = value / (2.0 ** exp) - 1.0
        exp_biased = exp + 127
        if exp_biased <= 0:
            # Subnormal
            exp_biased = 0
            mantissa = value / (2.0 ** (-126))
        elif exp_biased >= 255:
            # Overflow -> infinity
            return _float_to_bytes_32(math.copysign(math.inf, value if sign == 0 else -value), big_endian)
        mantissa_bits = int(round(mantissa * (1 << 23)))
        if mantissa_bits >= (1 << 23):
            mantissa_bits = (1 << 23) - 1
        bits = (sign << 31) | (exp_biased << 23) | mantissa_bits

    result = []
    for _ in range(4):
        result.append(bits & 0xFF)
        bits >>= 8
    if big_endian:
        result.reverse()
    return bytes(result)


def _bytes_to_float_32(data, big_endian):
    """Unpack 4 bytes into a Python float (IEEE 754 single precision)."""
    if big_endian:
        data = bytes(reversed(data))
    bits = 0
    for i, b in enumerate(data):
        bits |= b << (8 * i)

    sign = (bits >> 31) & 1
    exp_biased = (bits >> 23) & 0xFF
    mantissa_bits = bits & 0x7FFFFF

    if exp_biased == 255:
        if mantissa_bits == 0:
            value = math.inf
        else:
            value = math.nan
    elif exp_biased == 0:
        # Subnormal
        value = mantissa_bits / (1 << 23) * (2.0 ** (-126))
    else:
        value = (1.0 + mantissa_bits / (1 << 23)) * (2.0 ** (exp_biased - 127))

    if sign:
        value = -value
    return value


def _float_to_bytes_64(value, big_endian):
    """Pack a Python float into 8 bytes (IEEE 754 double precision)."""
    if math.isnan(value):
        bits = 0x7FF8000000000000
    elif math.isinf(value):
        if value > 0:
            bits = 0x7FF0000000000000
        else:
            bits = 0xFFF0000000000000
    elif value == 0.0:
        if math.copysign(1.0, value) < 0:
            bits = 0x8000000000000000
        else:
            bits = 0x0000000000000000
    else:
        sign = 0
        if value < 0:
            sign = 1
            value = -value
        exp = math.floor(math.log2(value))
        mantissa = value / (2.0 ** exp) - 1.0
        exp_biased = exp + 1023
        if exp_biased <= 0:
            exp_biased = 0
            mantissa = value / (2.0 ** (-1022))
        elif exp_biased >= 2047:
            return _float_to_bytes_64(math.copysign(math.inf, 1.0 if sign == 0 else -1.0), big_endian)
        mantissa_bits = int(round(mantissa * (1 << 52)))
        if mantissa_bits >= (1 << 52):
            mantissa_bits = (1 << 52) - 1
        bits = (sign << 63) | (exp_biased << 52) | mantissa_bits

    result = []
    for _ in range(8):
        result.append(bits & 0xFF)
        bits >>= 8
    if big_endian:
        result.reverse()
    return bytes(result)


def _bytes_to_float_64(data, big_endian):
    """Unpack 8 bytes into a Python float (IEEE 754 double precision)."""
    if big_endian:
        data = bytes(reversed(data))
    bits = 0
    for i, b in enumerate(data):
        bits |= b << (8 * i)

    sign = (bits >> 63) & 1
    exp_biased = (bits >> 52) & 0x7FF
    mantissa_bits = bits & 0x000FFFFFFFFFFFFF

    if exp_biased == 2047:
        if mantissa_bits == 0:
            value = math.inf
        else:
            value = math.nan
    elif exp_biased == 0:
        value = mantissa_bits / (1 << 52) * (2.0 ** (-1022))
    else:
        value = (1.0 + mantissa_bits / (1 << 52)) * (2.0 ** (exp_biased - 1023))

    if sign:
        value = -value
    return value


# ---------------------------------------------------------------------------
# Byte order helpers
# ---------------------------------------------------------------------------

def _is_big_endian(byte_order):
    if byte_order in ('>', '!'):
        return True
    if byte_order == '<':
        return False
    # '=' means native
    return sys.byteorder == 'big'


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------

def pack(fmt, *values):
    """Pack values into bytes according to format string."""
    byte_order, items = _parse_fmt(fmt)
    big_endian = _is_big_endian(byte_order)

    result = bytearray()
    val_idx = 0

    for count, ch in items:
        if ch == 'x':
            # Pad bytes - no value consumed
            result.extend(b'\x00' * count)
        elif ch == 's':
            # String: count bytes, one value
            val = values[val_idx]
            val_idx += 1
            if isinstance(val, str):
                val = val.encode('latin-1')
            # Pad or truncate to count bytes
            if len(val) < count:
                val = val + b'\x00' * (count - len(val))
            else:
                val = val[:count]
            result.extend(val)
        elif ch == 'p':
            # Pascal string: count bytes total, first byte is length
            val = values[val_idx]
            val_idx += 1
            if isinstance(val, str):
                val = val.encode('latin-1')
            max_len = count - 1
            if len(val) > max_len:
                val = val[:max_len]
            result.append(len(val))
            result.extend(val)
            # Pad to count bytes
            pad = count - 1 - len(val)
            result.extend(b'\x00' * pad)
        elif ch == 'c':
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                if isinstance(val, str):
                    val = val.encode('latin-1')
                if len(val) != 1:
                    raise ValueError("char format requires a bytes object of length 1")
                result.extend(val)
        elif ch == '?':
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                result.append(1 if val else 0)
        elif ch in ('b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q'):
            signed = ch in ('b', 'h', 'i', 'l', 'q')
            size = _FMT_SIZES[ch]
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                result.extend(_int_to_bytes(int(val), size, signed, big_endian))
        elif ch == 'f':
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                result.extend(_float_to_bytes_32(float(val), big_endian))
        elif ch == 'd':
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                result.extend(_float_to_bytes_64(float(val), big_endian))
        else:
            raise ValueError(f"Unknown format character: {ch!r}")

    return bytes(result)


# ---------------------------------------------------------------------------
# unpack
# ---------------------------------------------------------------------------

def unpack(fmt, buffer):
    """Unpack bytes into a tuple of values according to format string."""
    byte_order, items = _parse_fmt(fmt)
    big_endian = _is_big_endian(byte_order)

    expected = calcsize(fmt)
    if len(buffer) != expected:
        raise ValueError(
            f"unpack requires a buffer of {expected} bytes, got {len(buffer)}"
        )

    result = []
    offset = 0

    for count, ch in items:
        if ch == 'x':
            offset += count
        elif ch == 's':
            result.append(bytes(buffer[offset:offset + count]))
            offset += count
        elif ch == 'p':
            length = buffer[offset]
            max_len = count - 1
            actual_len = min(length, max_len)
            result.append(bytes(buffer[offset + 1:offset + 1 + actual_len]))
            offset += count
        elif ch == 'c':
            for _ in range(count):
                result.append(bytes([buffer[offset]]))
                offset += 1
        elif ch == '?':
            for _ in range(count):
                result.append(bool(buffer[offset]))
                offset += 1
        elif ch in ('b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q'):
            signed = ch in ('b', 'h', 'i', 'l', 'q')
            size = _FMT_SIZES[ch]
            for _ in range(count):
                chunk = buffer[offset:offset + size]
                result.append(_bytes_to_int(chunk, signed, big_endian))
                offset += size
        elif ch == 'f':
            for _ in range(count):
                chunk = buffer[offset:offset + 4]
                result.append(_bytes_to_float_32(chunk, big_endian))
                offset += 4
        elif ch == 'd':
            for _ in range(count):
                chunk = buffer[offset:offset + 8]
                result.append(_bytes_to_float_64(chunk, big_endian))
                offset += 8
        else:
            raise ValueError(f"Unknown format character: {ch!r}")

    return tuple(result)


# ---------------------------------------------------------------------------
# pack_into
# ---------------------------------------------------------------------------

def pack_into(fmt, buffer, offset, *values):
    """Pack values into buffer starting at offset."""
    data = pack(fmt, *values)
    size = len(data)
    if offset + size > len(buffer):
        raise ValueError("pack_into: buffer too small")
    buffer[offset:offset + size] = data


# ---------------------------------------------------------------------------
# unpack_from
# ---------------------------------------------------------------------------

def unpack_from(fmt, buffer, offset=0):
    """Unpack values from buffer starting at offset."""
    size = calcsize(fmt)
    return unpack(fmt, buffer[offset:offset + size])


# ---------------------------------------------------------------------------
# Zero-arg invariant functions
# ---------------------------------------------------------------------------

def struct3_calcsize():
    """calcsize('>HI') == 6"""
    return calcsize('>HI')


def struct3_pack_multi():
    """pack('>BH', 1, 2)[0] == 1"""
    return pack('>BH', 1, 2)[0]


def struct3_unpack_multi():
    """unpack('>BH', b'\\x01\\x00\\x02')[1] == 2"""
    return unpack('>BH', b'\x01\x00\x02')[1]