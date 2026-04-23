"""
theseus_struct_cr4 — Clean-room struct utilities with 'x' pad and '?' bool support.
Do NOT import struct or any third-party library.
"""

import sys

# ---------------------------------------------------------------------------
# Format character definitions
# ---------------------------------------------------------------------------
# Each entry: (size_in_bytes, signed, is_float, is_bool, is_pad, is_char, is_pascal)
# We'll use a simpler approach with a dispatch table.

_FMT_INFO = {
    # fmt_char: (size, kind)
    # kind: 'pad', 'bool', 'int_s', 'int_u', 'float', 'char', 'pascal'
    'x': (1, 'pad'),
    '?': (1, 'bool'),
    'b': (1, 'int_s'),
    'B': (1, 'int_u'),
    'h': (2, 'int_s'),
    'H': (2, 'int_u'),
    'i': (4, 'int_s'),
    'I': (4, 'int_u'),
    'l': (4, 'int_s'),
    'L': (4, 'int_u'),
    'q': (8, 'int_s'),
    'Q': (8, 'int_u'),
    'n': (8, 'int_s'),   # ssize_t — treat as 8 bytes (platform-ish, use 8)
    'N': (8, 'int_u'),   # size_t
    'e': (2, 'float'),
    'f': (4, 'float'),
    'd': (8, 'float'),
    's': (1, 'char'),
    'p': (1, 'pascal'),
}

# Native size overrides (for '@' and '=' and no-prefix modes)
# We'll use fixed sizes for simplicity (standard mode)
_NATIVE_SIZE = {
    'b': 1, 'B': 1,
    'h': 2, 'H': 2,
    'i': 4, 'I': 4,
    'l': 8 if sys.maxsize > 2**32 else 4,
    'L': 8 if sys.maxsize > 2**32 else 4,
    'q': 8, 'Q': 8,
    'n': 8 if sys.maxsize > 2**32 else 4,
    'N': 8 if sys.maxsize > 2**32 else 4,
    'e': 2, 'f': 4, 'd': 8,
    'x': 1, '?': 1, 's': 1, 'p': 1,
}

# ---------------------------------------------------------------------------
# Endianness / byte-order prefix parsing
# ---------------------------------------------------------------------------

def _parse_prefix(fmt):
    """
    Returns (byte_order, native_size, native_align, rest_of_fmt).
    byte_order: 'big' or 'little'
    native_size: bool — use native sizes?
    native_align: bool — use native alignment?
    """
    if not fmt:
        return 'native', True, True, fmt
    c = fmt[0]
    if c == '@':
        return 'native', True, True, fmt[1:]
    elif c == '=':
        return 'native', True, False, fmt[1:]
    elif c in ('<',):
        return 'little', False, False, fmt[1:]
    elif c in ('>', '!'):
        return 'big', False, False, fmt[1:]
    else:
        # No prefix — native byte order, native size
        return 'native', True, True, fmt

def _native_byte_order():
    return 'little' if sys.byteorder == 'little' else 'big'

# ---------------------------------------------------------------------------
# Format string tokenizer
# ---------------------------------------------------------------------------

def _tokenize(fmt_rest):
    """
    Yields (count, fmt_char) pairs from the format string (after prefix removed).
    e.g. '3I2x?' -> [(3,'I'), (2,'x'), (1,'?')]
    """
    i = 0
    while i < len(fmt_rest):
        c = fmt_rest[i]
        if c.isdigit():
            j = i
            while j < len(fmt_rest) and fmt_rest[j].isdigit():
                j += 1
            count = int(fmt_rest[i:j])
            i = j
            if i < len(fmt_rest):
                fc = fmt_rest[i]
                i += 1
                yield (count, fc)
        elif c == ' ':
            i += 1
        else:
            yield (1, c)
            i += 1

# ---------------------------------------------------------------------------
# Size calculation
# ---------------------------------------------------------------------------

def _fmt_size(fc, use_native_size):
    if fc not in _FMT_INFO:
        raise Exception(f"Unknown format character: {fc!r}")
    std_size, kind = _FMT_INFO[fc]
    if use_native_size and fc in _NATIVE_SIZE:
        return _NATIVE_SIZE[fc]
    return std_size

def calcsize(fmt):
    """Return the size of the struct corresponding to the format string fmt."""
    byte_order, use_native_size, use_native_align, rest = _parse_prefix(fmt)
    total = 0
    for count, fc in _tokenize(rest):
        if fc == 's' or fc == 'p':
            # count bytes for a single string item
            total += count
        else:
            sz = _fmt_size(fc, use_native_size)
            total += sz * count
    return total

# ---------------------------------------------------------------------------
# Float helpers (IEEE 754)
# ---------------------------------------------------------------------------

def _float_to_bytes_double(value):
    """Pack a Python float as IEEE 754 double (8 bytes), big-endian."""
    import math
    if math.isnan(value):
        # canonical NaN
        return bytes([0x7F, 0xF8, 0, 0, 0, 0, 0, 0])
    if math.isinf(value):
        if value > 0:
            return bytes([0x7F, 0xF0, 0, 0, 0, 0, 0, 0])
        else:
            return bytes([0xFF, 0xF0, 0, 0, 0, 0, 0, 0])
    if value == 0.0:
        # check sign
        import math
        if math.copysign(1.0, value) < 0:
            return bytes([0x80, 0, 0, 0, 0, 0, 0, 0])
        return bytes(8)

    sign = 0
    if value < 0:
        sign = 1
        value = -value

    import math
    exp = math.floor(math.log2(value))
    mantissa = value / (2.0 ** exp) - 1.0  # in [0, 1)

    # exponent bias for double: 1023
    biased_exp = exp + 1023
    if biased_exp <= 0:
        # subnormal
        biased_exp = 0
        mantissa = value / (2.0 ** (-1022))

    # mantissa has 52 bits
    mantissa_int = int(mantissa * (2**52) + 0.5)
    if mantissa_int >= 2**52:
        mantissa_int = 0
        biased_exp += 1

    bits = (sign << 63) | (biased_exp << 52) | mantissa_int
    result = []
    for _ in range(8):
        result.append(bits & 0xFF)
        bits >>= 8
    result.reverse()
    return bytes(result)

def _bytes_to_float_double(data):
    """Unpack IEEE 754 double (8 bytes, big-endian) to Python float."""
    import math
    bits = 0
    for b in data:
        bits = (bits << 8) | b
    sign = (bits >> 63) & 1
    exp = (bits >> 52) & 0x7FF
    mantissa = bits & ((1 << 52) - 1)

    if exp == 0x7FF:
        if mantissa == 0:
            val = float('inf')
        else:
            val = float('nan')
    elif exp == 0:
        # subnormal
        val = mantissa * (2.0 ** (-1074))
    else:
        val = (1.0 + mantissa / (2**52)) * (2.0 ** (exp - 1023))

    if sign:
        val = -val
    return val

def _float_to_bytes_single(value):
    """Pack a Python float as IEEE 754 single (4 bytes), big-endian."""
    import math
    if math.isnan(value):
        return bytes([0x7F, 0xC0, 0, 0])
    if math.isinf(value):
        if value > 0:
            return bytes([0x7F, 0x80, 0, 0])
        else:
            return bytes([0xFF, 0x80, 0, 0])
    if value == 0.0:
        if math.copysign(1.0, value) < 0:
            return bytes([0x80, 0, 0, 0])
        return bytes(4)

    sign = 0
    if value < 0:
        sign = 1
        value = -value

    import math
    exp = math.floor(math.log2(value))
    mantissa = value / (2.0 ** exp) - 1.0

    biased_exp = exp + 127
    if biased_exp <= 0:
        biased_exp = 0
        mantissa = value / (2.0 ** (-126))

    mantissa_int = int(mantissa * (2**23) + 0.5)
    if mantissa_int >= 2**23:
        mantissa_int = 0
        biased_exp += 1

    bits = (sign << 31) | (biased_exp << 23) | mantissa_int
    result = []
    for _ in range(4):
        result.append(bits & 0xFF)
        bits >>= 8
    result.reverse()
    return bytes(result)

def _bytes_to_float_single(data):
    """Unpack IEEE 754 single (4 bytes, big-endian) to Python float."""
    bits = 0
    for b in data:
        bits = (bits << 8) | b
    sign = (bits >> 31) & 1
    exp = (bits >> 23) & 0xFF
    mantissa = bits & ((1 << 23) - 1)

    if exp == 0xFF:
        if mantissa == 0:
            val = float('inf')
        else:
            val = float('nan')
    elif exp == 0:
        val = mantissa * (2.0 ** (-149))
    else:
        val = (1.0 + mantissa / (2**23)) * (2.0 ** (exp - 127))

    if sign:
        val = -val
    return val

def _float_to_bytes_half(value):
    """Pack a Python float as IEEE 754 half (2 bytes), big-endian."""
    import math
    if math.isnan(value):
        return bytes([0x7E, 0x00])
    if math.isinf(value):
        if value > 0:
            return bytes([0x7C, 0x00])
        else:
            return bytes([0xFC, 0x00])
    if value == 0.0:
        if math.copysign(1.0, value) < 0:
            return bytes([0x80, 0x00])
        return bytes(2)

    sign = 0
    if value < 0:
        sign = 1
        value = -value

    exp = math.floor(math.log2(value))
    mantissa = value / (2.0 ** exp) - 1.0

    biased_exp = exp + 15
    if biased_exp <= 0:
        biased_exp = 0
        mantissa = value / (2.0 ** (-14))

    mantissa_int = int(mantissa * (2**10) + 0.5)
    if mantissa_int >= 2**10:
        mantissa_int = 0
        biased_exp += 1

    bits = (sign << 15) | (biased_exp << 10) | mantissa_int
    result = []
    for _ in range(2):
        result.append(bits & 0xFF)
        bits >>= 8
    result.reverse()
    return bytes(result)

def _bytes_to_float_half(data):
    """Unpack IEEE 754 half (2 bytes, big-endian) to Python float."""
    bits = 0
    for b in data:
        bits = (bits << 8) | b
    sign = (bits >> 15) & 1
    exp = (bits >> 10) & 0x1F
    mantissa = bits & ((1 << 10) - 1)

    if exp == 0x1F:
        if mantissa == 0:
            val = float('inf')
        else:
            val = float('nan')
    elif exp == 0:
        val = mantissa * (2.0 ** (-24))
    else:
        val = (1.0 + mantissa / (2**10)) * (2.0 ** (exp - 15))

    if sign:
        val = -val
    return val

# ---------------------------------------------------------------------------
# Integer pack/unpack helpers
# ---------------------------------------------------------------------------

def _int_to_bytes(value, size, signed, big_endian):
    """Convert integer to bytes."""
    if signed:
        if value < -(1 << (size * 8 - 1)) or value >= (1 << (size * 8 - 1)):
            raise Exception(f"Value {value} out of range for signed {size}-byte integer")
        if value < 0:
            value = value + (1 << (size * 8))
    else:
        if value < 0 or value >= (1 << (size * 8)):
            raise Exception(f"Value {value} out of range for unsigned {size}-byte integer")
    result = []
    for _ in range(size):
        result.append(value & 0xFF)
        value >>= 8
    if big_endian:
        result.reverse()
    return bytes(result)

def _bytes_to_int(data, signed, big_endian):
    """Convert bytes to integer."""
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
# Core pack implementation
# ---------------------------------------------------------------------------

def pack(fmt, *values):
    """Pack values according to format string."""
    byte_order, use_native_size, use_native_align, rest = _parse_prefix(fmt)

    if byte_order == 'native':
        big_endian = (_native_byte_order() == 'big')
    else:
        big_endian = (byte_order == 'big')

    result = bytearray()
    val_iter = iter(values)

    for count, fc in _tokenize(rest):
        if fc not in _FMT_INFO:
            raise Exception(f"Unknown format character: {fc!r}")
        _, kind = _FMT_INFO[fc]
        sz = _fmt_size(fc, use_native_size)

        if fc == 's':
            # 's' with count: single bytes object of length count
            val = next(val_iter)
            if isinstance(val, str):
                val = val.encode('latin-1')
            val = bytes(val)
            # pad or truncate to count bytes
            if len(val) < count:
                val = val + b'\x00' * (count - len(val))
            else:
                val = val[:count]
            result.extend(val)
        elif fc == 'p':
            # Pascal string: first byte is length, rest is data
            val = next(val_iter)
            if isinstance(val, str):
                val = val.encode('latin-1')
            val = bytes(val)
            max_len = count - 1
            if max_len < 0:
                max_len = 0
            data = val[:max_len]
            length_byte = len(data)
            result.append(length_byte)
            result.extend(data)
            # pad to count total bytes
            pad_needed = count - 1 - len(data)
            result.extend(b'\x00' * pad_needed)
        elif kind == 'pad':
            # 'x': pad byte, no value consumed
            result.extend(b'\x00' * count)
        elif kind == 'bool':
            for _ in range(count):
                val = next(val_iter)
                result.append(1 if val else 0)
        elif kind == 'int_u':
            for _ in range(count):
                val = next(val_iter)
                result.extend(_int_to_bytes(int(val), sz, False, big_endian))
        elif kind == 'int_s':
            for _ in range(count):
                val = next(val_iter)
                result.extend(_int_to_bytes(int(val), sz, True, big_endian))
        elif kind == 'float':
            for _ in range(count):
                val = next(val_iter)
                val = float(val)
                if sz == 8:
                    fb = _float_to_bytes_double(val)
                elif sz == 4:
                    fb = _float_to_bytes_single(val)
                elif sz == 2:
                    fb = _float_to_bytes_half(val)
                else:
                    raise Exception(f"Unsupported float size: {sz}")
                if not big_endian:
                    fb = bytes(reversed(fb))
                result.extend(fb)
        else:
            raise Exception(f"Unhandled kind: {kind}")

    return bytes(result)

# ---------------------------------------------------------------------------
# Core unpack implementation
# ---------------------------------------------------------------------------

def unpack(fmt, buffer):
    """Unpack buffer according to format string, returning a tuple."""
    byte_order, use_native_size, use_native_align, rest = _parse_prefix(fmt)

    if byte_order == 'native':
        big_endian = (_native_byte_order() == 'big')
    else:
        big_endian = (byte_order == 'big')

    if isinstance(buffer, (bytes, bytearray, memoryview)):
        buf = bytes(buffer)
    else:
        raise Exception("buffer must be bytes-like")

    expected = calcsize(fmt)
    if len(buf) != expected:
        raise Exception(
            f"unpack requires a buffer of {expected} bytes, got {len(buf)}"
        )

    result = []
    offset = 0

    for count, fc in _tokenize(rest):
        if fc not in _FMT_INFO:
            raise Exception(f"Unknown format character: {fc!r}")
        _, kind = _FMT_INFO[fc]
        sz = _fmt_size(fc, use_native_size)

        if fc == 's':
            chunk = buf[offset:offset + count]
            result.append(chunk)
            offset += count
        elif fc == 'p':
            # Pascal string
            length = buf[offset]
            max_len = count - 1
            data = buf[offset + 1: offset + 1 + min(length, max_len)]
            result.append(data)
            offset += count
        elif kind == 'pad':
            # skip pad bytes, no value added to result
            offset += count
        elif kind == 'bool':
            for _ in range(count):
                val = buf[offset]
                result.append(val != 0)
                offset += 1
        elif kind == 'int_u':
            for _ in range(count):
                chunk = buf[offset:offset + sz]
                result.append(_bytes_to_int(chunk, False, big_endian))
                offset += sz
        elif kind == 'int_s':
            for _ in range(count):
                chunk = buf[offset:offset + sz]
                result.append(_bytes_to_int(chunk, True, big_endian))
                offset += sz
        elif kind == 'float':
            for _ in range(count):
                chunk = buf[offset:offset + sz]
                if not big_endian:
                    chunk = bytes(reversed(chunk))
                if sz == 8:
                    val = _bytes_to_float_double(chunk)
                elif sz == 4:
                    val = _bytes_to_float_single(chunk)
                elif sz == 2:
                    val = _bytes_to_float_half(chunk)
                else:
                    raise Exception(f"Unsupported float size: {sz}")
                result.append(val)
                offset += sz
        else:
            raise Exception(f"Unhandled kind: {kind}")

    return tuple(result)

# ---------------------------------------------------------------------------
# pack_into / unpack_from
# ---------------------------------------------------------------------------

def pack_into(fmt, buffer, offset, *values):
    """Pack values into buffer at the given offset."""
    data = pack(fmt, *values)
    end = offset + len(data)
    if end > len(buffer):
        raise Exception(
            f"pack_into requires buffer of at least {end} bytes"
        )
    buffer[offset:end] = data

def unpack_from(fmt, buffer, offset=0):
    """Unpack from buffer starting at offset."""
    size = calcsize(fmt)
    chunk = bytes(buffer)[offset:offset + size]
    if len(chunk) < size:
        raise Exception(
            f"unpack_from requires at least {size} bytes starting at offset {offset}"
        )
    return unpack(fmt, chunk)

# ---------------------------------------------------------------------------
# Invariant test functions
# ---------------------------------------------------------------------------

def struct4_pad():
    """pack('>xBx', 255)[1] == 255 — returns the middle byte value."""
    result = pack('>xBx', 255)
    return result[1]

def struct4_bool():
    """pack('?', True)[0] == 1 — returns the byte value for True."""
    result = pack('?', True)
    return result[0]

def struct4_bool_unpack():
    """unpack('?', b'\\x01')[0] == True — returns the unpacked bool."""
    result = unpack('?', b'\x01')
    return result[0]