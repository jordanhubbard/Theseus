"""
theseus_struct_cr2: Clean-room implementation of struct utilities.
No import of the 'struct' module allowed.
"""

# Format character info: (size_in_bytes, signed)
# We support: x, c, b, B, h, H, i, I, l, L, q, Q, f, d, s, p, ?
# Byte order prefixes: @, =, <, >, !

_FORMAT_SIZES = {
    'x': 1,   # pad byte
    'c': 1,   # char
    'b': 1,   # signed char
    'B': 1,   # unsigned char
    '?': 1,   # bool
    'h': 2,   # short
    'H': 2,   # unsigned short
    'i': 4,   # int
    'I': 4,   # unsigned int
    'l': 4,   # long
    'L': 4,   # unsigned long
    'q': 8,   # long long
    'Q': 8,   # unsigned long long
    'f': 4,   # float
    'd': 8,   # double
    's': 1,   # char[] (special)
    'p': 1,   # pascal string (special)
    'n': 8,   # ssize_t (platform dependent, use 8)
    'N': 8,   # size_t
    'e': 2,   # half float
}

_SIGNED_FORMATS = {'b', 'h', 'i', 'l', 'q', 'n'}
_UNSIGNED_FORMATS = {'B', 'H', 'I', 'L', 'Q', 'N', '?'}
_FLOAT_FORMATS = {'f', 'd', 'e'}


def _parse_format(fmt):
    """
    Parse a format string into (byte_order, list_of_(count, char)).
    byte_order: 'big', 'little', 'native', 'network'
    Returns (byte_order, items) where items is list of (count, fmt_char)
    """
    if not fmt:
        raise ValueError("Empty format string")
    
    idx = 0
    byte_order = 'native'  # default
    
    # Check for byte order prefix
    if fmt[0] in ('@', '=', '<', '>', '!'):
        prefix = fmt[0]
        idx = 1
        if prefix == '<':
            byte_order = 'little'
        elif prefix in ('>', '!'):
            byte_order = 'big'
        elif prefix == '=':
            byte_order = 'native_std'  # native byte order, standard sizes
        else:  # '@'
            byte_order = 'native'
    
    items = []
    n = len(fmt)
    
    while idx < n:
        # Read optional count
        count_str = ''
        while idx < n and fmt[idx].isdigit():
            count_str += fmt[idx]
            idx += 1
        
        if idx >= n:
            if count_str:
                raise ValueError(f"Format string ended with digits: {fmt}")
            break
        
        fc = fmt[idx]
        idx += 1
        
        count = int(count_str) if count_str else 1
        
        if fc not in _FORMAT_SIZES and fc != 'x':
            raise ValueError(f"Unknown format character: {fc!r}")
        
        items.append((count, fc))
    
    return byte_order, items


def _calc_size(byte_order, items):
    """Calculate total size in bytes for parsed format items."""
    total = 0
    for count, fc in items:
        if fc in ('s', 'p'):
            # 's': count is the number of bytes for the string
            total += count
        else:
            size = _FORMAT_SIZES.get(fc, 0)
            total += size * count
    return total


def _int_to_bytes_big(value, size, signed):
    """Convert integer to bytes, big-endian."""
    if signed:
        if value < 0:
            # Two's complement
            value = value + (1 << (size * 8))
        max_val = (1 << (size * 8)) - 1
        if value < 0 or value > max_val:
            raise ValueError(f"Value {value} out of range for {size}-byte signed integer")
    else:
        if value < 0:
            raise ValueError(f"Value {value} is negative for unsigned integer")
        max_val = (1 << (size * 8)) - 1
        if value > max_val:
            raise ValueError(f"Value {value} out of range for {size}-byte unsigned integer")
    
    result = bytearray(size)
    for i in range(size - 1, -1, -1):
        result[i] = value & 0xFF
        value >>= 8
    return bytes(result)


def _int_to_bytes_little(value, size, signed):
    """Convert integer to bytes, little-endian."""
    if signed:
        if value < 0:
            value = value + (1 << (size * 8))
        max_val = (1 << (size * 8)) - 1
        if value < 0 or value > max_val:
            raise ValueError(f"Value {value} out of range for {size}-byte signed integer")
    else:
        if value < 0:
            raise ValueError(f"Value {value} is negative for unsigned integer")
        max_val = (1 << (size * 8)) - 1
        if value > max_val:
            raise ValueError(f"Value {value} out of range for {size}-byte unsigned integer")
    
    result = bytearray(size)
    for i in range(size):
        result[i] = value & 0xFF
        value >>= 8
    return bytes(result)


def _bytes_to_int_big(data, signed):
    """Convert bytes to integer, big-endian."""
    value = 0
    for b in data:
        value = (value << 8) | b
    if signed:
        size = len(data)
        if value >= (1 << (size * 8 - 1)):
            value -= (1 << (size * 8))
    return value


def _bytes_to_int_little(data, signed):
    """Convert bytes to integer, little-endian."""
    value = 0
    for i, b in enumerate(data):
        value |= b << (8 * i)
    if signed:
        size = len(data)
        if value >= (1 << (size * 8 - 1)):
            value -= (1 << (size * 8))
    return value


def _float_to_bytes_big(value, size):
    """Convert float to IEEE 754 bytes, big-endian."""
    if size == 4:
        return _float32_to_bytes(value, big_endian=True)
    elif size == 8:
        return _float64_to_bytes(value, big_endian=True)
    elif size == 2:
        return _float16_to_bytes(value, big_endian=True)
    else:
        raise ValueError(f"Unsupported float size: {size}")


def _float_to_bytes_little(value, size):
    """Convert float to IEEE 754 bytes, little-endian."""
    if size == 4:
        return _float32_to_bytes(value, big_endian=False)
    elif size == 8:
        return _float64_to_bytes(value, big_endian=False)
    elif size == 2:
        return _float16_to_bytes(value, big_endian=False)
    else:
        raise ValueError(f"Unsupported float size: {size}")


def _float32_to_bytes(value, big_endian=True):
    """Convert Python float to 4-byte IEEE 754 single precision."""
    import math
    if math.isnan(value):
        bits = 0x7FC00000
    elif math.isinf(value):
        if value > 0:
            bits = 0x7F800000
        else:
            bits = 0xFF800000
    elif value == 0.0:
        # Check for negative zero
        import math
        if math.copysign(1.0, value) < 0:
            bits = 0x80000000
        else:
            bits = 0
    else:
        sign = 0
        if value < 0:
            sign = 1
            value = -value
        
        exp = math.floor(math.log2(value))
        mantissa = value / (2.0 ** exp) - 1.0
        
        # Biased exponent for float32: bias = 127
        biased_exp = exp + 127
        
        if biased_exp <= 0:
            # Subnormal
            biased_exp = 0
            mantissa = value / (2.0 ** (-126))
        elif biased_exp >= 255:
            # Overflow -> infinity
            return _float_to_bytes_big(float('inf') if sign == 0 else float('-inf'), 4) if big_endian else _float_to_bytes_little(float('inf') if sign == 0 else float('-inf'), 4)
        
        mantissa_bits = int(mantissa * (1 << 23) + 0.5) & 0x7FFFFF
        bits = (sign << 31) | (biased_exp << 23) | mantissa_bits
    
    result = bytearray(4)
    if big_endian:
        for i in range(3, -1, -1):
            result[i] = bits & 0xFF
            bits >>= 8
    else:
        for i in range(4):
            result[i] = bits & 0xFF
            bits >>= 8
    return bytes(result)


def _float64_to_bytes(value, big_endian=True):
    """Convert Python float to 8-byte IEEE 754 double precision."""
    import math
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
            bits = 0
    else:
        sign = 0
        if value < 0:
            sign = 1
            value = -value
        
        exp = math.floor(math.log2(value))
        mantissa = value / (2.0 ** exp) - 1.0
        
        biased_exp = exp + 1023
        
        if biased_exp <= 0:
            biased_exp = 0
            mantissa = value / (2.0 ** (-1022))
        elif biased_exp >= 2047:
            if sign == 0:
                bits = 0x7FF0000000000000
            else:
                bits = 0xFFF0000000000000
            result = bytearray(8)
            if big_endian:
                for i in range(7, -1, -1):
                    result[i] = bits & 0xFF
                    bits >>= 8
            else:
                for i in range(8):
                    result[i] = bits & 0xFF
                    bits >>= 8
            return bytes(result)
        
        mantissa_bits = int(mantissa * (1 << 52) + 0.5) & 0x000FFFFFFFFFFFFF
        bits = (sign << 63) | (biased_exp << 52) | mantissa_bits
    
    result = bytearray(8)
    if big_endian:
        for i in range(7, -1, -1):
            result[i] = bits & 0xFF
            bits >>= 8
    else:
        for i in range(8):
            result[i] = bits & 0xFF
            bits >>= 8
    return bytes(result)


def _float16_to_bytes(value, big_endian=True):
    """Convert Python float to 2-byte IEEE 754 half precision."""
    import math
    if math.isnan(value):
        bits = 0x7E00
    elif math.isinf(value):
        bits = 0x7C00 if value > 0 else 0xFC00
    elif value == 0.0:
        if math.copysign(1.0, value) < 0:
            bits = 0x8000
        else:
            bits = 0
    else:
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
        elif biased_exp >= 31:
            bits = 0x7C00 | (sign << 15)
            result = bytearray(2)
            if big_endian:
                result[0] = (bits >> 8) & 0xFF
                result[1] = bits & 0xFF
            else:
                result[0] = bits & 0xFF
                result[1] = (bits >> 8) & 0xFF
            return bytes(result)
        
        mantissa_bits = int(mantissa * (1 << 10) + 0.5) & 0x3FF
        bits = (sign << 15) | (biased_exp << 10) | mantissa_bits
    
    result = bytearray(2)
    if big_endian:
        result[0] = (bits >> 8) & 0xFF
        result[1] = bits & 0xFF
    else:
        result[0] = bits & 0xFF
        result[1] = (bits >> 8) & 0xFF
    return bytes(result)


def _bytes_to_float32(data, big_endian=True):
    """Convert 4 bytes to Python float (IEEE 754 single)."""
    import math
    if big_endian:
        bits = 0
        for b in data:
            bits = (bits << 8) | b
    else:
        bits = 0
        for i, b in enumerate(data):
            bits |= b << (8 * i)
    
    sign = (bits >> 31) & 1
    exp = (bits >> 23) & 0xFF
    mantissa = bits & 0x7FFFFF
    
    if exp == 255:
        if mantissa == 0:
            return float('-inf') if sign else float('inf')
        else:
            return float('nan')
    elif exp == 0:
        value = mantissa / (1 << 23) * (2.0 ** (-126))
    else:
        value = (1.0 + mantissa / (1 << 23)) * (2.0 ** (exp - 127))
    
    return -value if sign else value


def _bytes_to_float64(data, big_endian=True):
    """Convert 8 bytes to Python float (IEEE 754 double)."""
    if big_endian:
        bits = 0
        for b in data:
            bits = (bits << 8) | b
    else:
        bits = 0
        for i, b in enumerate(data):
            bits |= b << (8 * i)
    
    sign = (bits >> 63) & 1
    exp = (bits >> 52) & 0x7FF
    mantissa = bits & 0x000FFFFFFFFFFFFF
    
    if exp == 2047:
        if mantissa == 0:
            return float('-inf') if sign else float('inf')
        else:
            return float('nan')
    elif exp == 0:
        value = mantissa / (1 << 52) * (2.0 ** (-1022))
    else:
        value = (1.0 + mantissa / (1 << 52)) * (2.0 ** (exp - 1023))
    
    return -value if sign else value


def _bytes_to_float16(data, big_endian=True):
    """Convert 2 bytes to Python float (IEEE 754 half)."""
    if big_endian:
        bits = (data[0] << 8) | data[1]
    else:
        bits = data[0] | (data[1] << 8)
    
    sign = (bits >> 15) & 1
    exp = (bits >> 10) & 0x1F
    mantissa = bits & 0x3FF
    
    if exp == 31:
        if mantissa == 0:
            return float('-inf') if sign else float('inf')
        else:
            return float('nan')
    elif exp == 0:
        value = mantissa / (1 << 10) * (2.0 ** (-14))
    else:
        value = (1.0 + mantissa / (1 << 10)) * (2.0 ** (exp - 15))
    
    return -value if sign else value


def _is_big_endian_system():
    """Detect native byte order."""
    # Use a simple test
    val = 0x0102
    b = bytearray(2)
    b[0] = (val >> 8) & 0xFF
    b[1] = val & 0xFF
    # On big-endian, storing MSB first is natural
    # We'll just check sys.byteorder if available
    import sys
    return sys.byteorder == 'big'


def _pack_items(byte_order, items, values):
    """Pack values according to parsed format items."""
    big_endian = byte_order in ('big', 'network')
    if byte_order == 'native':
        big_endian = _is_big_endian_system()
    elif byte_order == 'native_std':
        big_endian = _is_big_endian_system()
    
    result = bytearray()
    val_idx = 0
    
    for count, fc in items:
        if fc == 'x':
            # Pad byte, no value consumed
            result.extend(b'\x00' * count)
        elif fc == 's':
            # String: count bytes, one value
            val = values[val_idx]
            val_idx += 1
            if isinstance(val, str):
                val = val.encode('latin-1')
            elif isinstance(val, (bytearray, memoryview)):
                val = bytes(val)
            # Pad or truncate to count bytes
            if len(val) < count:
                val = val + b'\x00' * (count - len(val))
            else:
                val = val[:count]
            result.extend(val)
        elif fc == 'p':
            # Pascal string: first byte is length, rest is data
            val = values[val_idx]
            val_idx += 1
            if isinstance(val, str):
                val = val.encode('latin-1')
            elif isinstance(val, (bytearray, memoryview)):
                val = bytes(val)
            # count is total size including length byte
            max_len = min(count - 1, 255)
            data = val[:max_len]
            result.append(len(data))
            result.extend(data)
            # Pad to count bytes
            pad = count - 1 - len(data)
            if pad > 0:
                result.extend(b'\x00' * pad)
        elif fc == 'c':
            # Single char
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                if isinstance(val, int):
                    result.append(val & 0xFF)
                elif isinstance(val, (bytes, bytearray)):
                    result.append(val[0])
                else:
                    result.append(ord(val))
        elif fc == '?':
            # Bool
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                result.append(1 if val else 0)
        elif fc in _SIGNED_FORMATS or fc in _UNSIGNED_FORMATS:
            signed = fc in _SIGNED_FORMATS
            size = _FORMAT_SIZES[fc]
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                if not isinstance(val, int):
                    val = int(val)
                if big_endian:
                    result.extend(_int_to_bytes_big(val, size, signed))
                else:
                    result.extend(_int_to_bytes_little(val, size, signed))
        elif fc in _FLOAT_FORMATS:
            size = _FORMAT_SIZES[fc]
            for _ in range(count):
                val = values[val_idx]
                val_idx += 1
                if not isinstance(val, float):
                    val = float(val)
                if big_endian:
                    result.extend(_float_to_bytes_big(val, size))
                else:
                    result.extend(_float_to_bytes_little(val, size))
        else:
            raise ValueError(f"Unsupported format character: {fc!r}")
    
    return bytes(result)


def _unpack_items(byte_order, items, data, offset=0):
    """Unpack values from data according to parsed format items."""
    big_endian = byte_order in ('big', 'network')
    if byte_order == 'native':
        big_endian = _is_big_endian_system()
    elif byte_order == 'native_std':
        big_endian = _is_big_endian_system()
    
    result = []
    pos = offset
    
    for count, fc in items:
        if fc == 'x':
            # Pad byte, skip
            pos += count
        elif fc == 's':
            # String: count bytes as one value
            chunk = data[pos:pos + count]
            result.append(bytes(chunk))
            pos += count
        elif fc == 'p':
            # Pascal string
            length = data[pos]
            max_len = min(length, count - 1)
            chunk = data[pos + 1:pos + 1 + max_len]
            result.append(bytes(chunk))
            pos += count
        elif fc == 'c':
            for _ in range(count):
                result.append(bytes([data[pos]]))
                pos += 1
        elif fc == '?':
            for _ in range(count):
                result.append(bool(data[pos]))
                pos += 1
        elif fc in _SIGNED_FORMATS or fc in _UNSIGNED_FORMATS:
            signed = fc in _SIGNED_FORMATS
            size = _FORMAT_SIZES[fc]
            for _ in range(count):
                chunk = data[pos:pos + size]
                if big_endian:
                    val = _bytes_to_int_big(chunk, signed)
                else:
                    val = _bytes_to_int_little(chunk, signed)
                result.append(val)
                pos += size
        elif fc in _FLOAT_FORMATS:
            size = _FORMAT_SIZES[fc]
            for _ in range(count):
                chunk = data[pos:pos + size]
                if size == 4:
                    val = _bytes_to_float32(chunk, big_endian)
                elif size == 8:
                    val = _bytes_to_float64(chunk, big_endian)
                elif size == 2:
                    val = _bytes_to_float16(chunk, big_endian)
                else:
                    raise ValueError(f"Unsupported float size: {size}")
                result.append(val)
                pos += size
        else:
            raise ValueError(f"Unsupported format character: {fc!r}")
    
    return tuple(result)


def _count_values(items):
    """Count the number of values produced/consumed by format items."""
    count = 0
    for n, fc in items:
        if fc == 'x':
            pass  # no value
        elif fc in ('s', 'p'):
            count += 1  # one value per 's' or 'p' regardless of count
        else:
            count += n
    return count


def pack(fmt, *values):
    """Pack values according to format string."""
    byte_order, items = _parse_format(fmt)
    return _pack_items(byte_order, items, values)


def unpack(fmt, buffer):
    """Unpack values from buffer according to format string."""
    byte_order, items = _parse_format(fmt)
    return _unpack_items(byte_order, items, buffer, 0)


def pack_into(fmt, buffer, offset, *values):
    """Pack values into buffer at offset according to format string."""
    byte_order, items = _parse_format(fmt)
    data = _pack_items(byte_order, items, values)
    for i, b in enumerate(data):
        buffer[offset + i] = b


def unpack_from(fmt, buffer, offset=0):
    """Unpack values from buffer at offset according to format string."""
    byte_order, items = _parse_format(fmt)
    return _unpack_items(byte_order, items, buffer, offset)


def iter_unpack(fmt, buffer):
    """Iterate over successive packed items in buffer."""
    byte_order, items = _parse_format(fmt)
    size = _calc_size(byte_order, items)
    if size == 0:
        raise ValueError("iter_unpack requires a format with a non-zero size")
    offset = 0
    buf_len = len(buffer)
    while offset + size <= buf_len:
        yield _unpack_items(byte_order, items, buffer, offset)
        offset += size


def calcsize(fmt):
    """Return the size of the struct corresponding to the format string."""
    byte_order, items = _parse_format(fmt)
    return _calc_size(byte_order, items)


class Struct:
    """
    Compiled struct format object.
    """
    
    def __init__(self, fmt):
        self.format = fmt
        self._byte_order, self._items = _parse_format(fmt)
        self.size = _calc_size(self._byte_order, self._items)
    
    def pack(self, *values):
        """Pack values according to this struct's format."""
        return _pack_items(self._byte_order, self._items, values)
    
    def unpack(self, buffer):
        """Unpack values from buffer."""
        if len(buffer) < self.size:
            raise ValueError(
                f"unpack requires a buffer of at least {self.size} bytes, "
                f"got {len(buffer)}"
            )
        return _unpack_items(self._byte_order, self._items, buffer, 0)
    
    def pack_into(self, buffer, offset, *values):
        """Pack values into buffer at offset."""
        data = _pack_items(self._byte_order, self._items, values)
        for i, b in enumerate(data):
            buffer[offset + i] = b
    
    def unpack_from(self, buffer, offset=0):
        """Unpack values from buffer at offset."""
        return _unpack_items(self._byte_order, self._items, buffer, offset)
    
    def iter_unpack(self, buffer):
        """Iterate over successive packed items in buffer."""
        if self.size == 0:
            raise ValueError("iter_unpack requires a format with a non-zero size")
        offset = 0
        buf_len = len(buffer)
        while offset + self.size <= buf_len:
            yield _unpack_items(self._byte_order, self._items, buffer, offset)
            offset += self.size
    
    def __repr__(self):
        return f"Struct({self.format!r})"


# --- Invariant test functions ---

def struct2_struct_size():
    """Struct('>I').size == 4"""
    return Struct('>I').size


def struct2_pack_into():
    """pack_into('>H', buf, 0, 0x1234); buf[0]==0x12 → returns 0x12 = 18"""
    buf = bytearray(2)
    pack_into('>H', buf, 0, 0x1234)
    return buf[0]


def struct2_unpack_from():
    """unpack_from('>H', b'\\x00\\x42', 0) == (0x42,) → returns 66"""
    result = unpack_from('>H', b'\x00\x42', 0)
    return result[0]