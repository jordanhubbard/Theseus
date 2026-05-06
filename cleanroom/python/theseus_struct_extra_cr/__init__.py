# Clean-room implementation of a subset of Python's struct module.
# No import of `struct` or any third-party library — only stdlib built-ins.

_SIZES = {
    'b': 1, 'B': 1, '?': 1, 'c': 1, 'x': 1,
    'h': 2, 'H': 2,
    'i': 4, 'I': 4, 'l': 4, 'L': 4,
    'q': 8, 'Q': 8,
}

_INT_CHARS = ('b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q')
_SIGNED = ('b', 'h', 'i', 'l', 'q')


def _parse_format(fmt):
    """Parse a format string into (byte_order, [(count, char), ...])."""
    if fmt is None:
        raise ValueError("format must not be None")
    if isinstance(fmt, bytes):
        fmt = fmt.decode('ascii')
    byte_order = '@'
    i = 0
    if len(fmt) > 0 and fmt[0] in '<>!=@':
        byte_order = fmt[0]
        i = 1
    items = []
    n_buf = ''
    while i < len(fmt):
        c = fmt[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            n_buf += c
            i += 1
            continue
        count = int(n_buf) if n_buf else 1
        n_buf = ''
        items.append((count, c))
        i += 1
    if n_buf:
        raise ValueError("trailing repeat count without format char")
    return byte_order, items


def _is_big_endian(byte_order):
    # '<' little, '>' / '!' big, '=' / '@' native (treated as little-endian here)
    return byte_order in ('>', '!')


def calcsize(fmt):
    _, items = _parse_format(fmt)
    total = 0
    for count, ch in items:
        if ch == 's' or ch == 'p':
            total += count
        elif ch in _SIZES:
            total += _SIZES[ch] * count
        else:
            raise ValueError("bad char in struct format: " + repr(ch))
    return total


def _pack_int(value, size, signed, big_endian):
    if not isinstance(value, int) or isinstance(value, bool):
        if isinstance(value, bool):
            value = int(value)
        else:
            raise TypeError("required argument is not an integer")
    if signed:
        bound = 1 << (size * 8 - 1)
        if value < -bound or value >= bound:
            raise OverflowError("integer out of range for format")
        if value < 0:
            value += (1 << (size * 8))
    else:
        limit = 1 << (size * 8)
        if value < 0 or value >= limit:
            raise OverflowError("integer out of range for format")
    out = bytearray(size)
    v = value
    for j in range(size):
        out[j] = v & 0xFF
        v >>= 8
    if big_endian:
        out.reverse()
    return bytes(out)


def _unpack_int(chunk, signed, big_endian):
    size = len(chunk)
    data = bytes(reversed(chunk)) if big_endian else bytes(chunk)
    val = 0
    for j in range(size - 1, -1, -1):
        val = (val << 8) | data[j]
    if signed:
        bound = 1 << (size * 8 - 1)
        if val >= bound:
            val -= (1 << (size * 8))
    return val


def pack(fmt, *values):
    byte_order, items = _parse_format(fmt)
    big_endian = _is_big_endian(byte_order)
    out = bytearray()
    idx = 0
    for count, ch in items:
        if ch == 'x':
            out.extend(b'\x00' * count)
            continue
        if ch == 's':
            if idx >= len(values):
                raise ValueError("not enough values to pack")
            v = values[idx]
            idx += 1
            if isinstance(v, str):
                v = v.encode('latin-1')
            if not isinstance(v, (bytes, bytearray)):
                raise TypeError("string format requires bytes")
            if len(v) >= count:
                out.extend(bytes(v[:count]))
            else:
                out.extend(bytes(v))
                out.extend(b'\x00' * (count - len(v)))
            continue
        # per-element format char
        for _ in range(count):
            if idx >= len(values):
                raise ValueError("not enough values to pack")
            v = values[idx]
            idx += 1
            if ch in _INT_CHARS:
                size = _SIZES[ch]
                signed = ch in _SIGNED
                out.extend(_pack_int(int(v), size, signed, big_endian))
            elif ch == '?':
                out.append(1 if v else 0)
            elif ch == 'c':
                if isinstance(v, str):
                    v = v.encode('latin-1')
                if not isinstance(v, (bytes, bytearray)) or len(v) != 1:
                    raise TypeError("char format requires a single-byte bytes object")
                out.append(v[0])
            else:
                raise ValueError("bad char in struct format: " + repr(ch))
    if idx != len(values):
        raise ValueError("too many values to pack")
    return bytes(out)


def unpack(fmt, buffer):
    byte_order, items = _parse_format(fmt)
    big_endian = _is_big_endian(byte_order)
    expected = calcsize(fmt)
    if isinstance(buffer, (bytearray, memoryview)):
        buffer = bytes(buffer)
    if not isinstance(buffer, bytes):
        raise TypeError("buffer must be bytes-like")
    if len(buffer) != expected:
        raise ValueError(
            "unpack requires a buffer of %d bytes (got %d)" % (expected, len(buffer))
        )
    result = []
    pos = 0
    for count, ch in items:
        if ch == 'x':
            pos += count
            continue
        if ch == 's':
            result.append(buffer[pos:pos + count])
            pos += count
            continue
        for _ in range(count):
            if ch in _INT_CHARS:
                size = _SIZES[ch]
                signed = ch in _SIGNED
                chunk = buffer[pos:pos + size]
                pos += size
                result.append(_unpack_int(chunk, signed, big_endian))
            elif ch == '?':
                result.append(buffer[pos] != 0)
                pos += 1
            elif ch == 'c':
                result.append(buffer[pos:pos + 1])
                pos += 1
            else:
                raise ValueError("bad char in struct format: " + repr(ch))
    return tuple(result)


def pack_into(fmt, buf, offset, *values):
    data = pack(fmt, *values)
    if not isinstance(buf, bytearray):
        raise TypeError("buffer must be a writable bytearray")
    end = offset + len(data)
    if end > len(buf):
        raise ValueError("buffer too small")
    buf[offset:end] = data


def unpack_from(fmt, buffer, offset=0):
    size = calcsize(fmt)
    if isinstance(buffer, (bytearray, memoryview)):
        buffer = bytes(buffer)
    return unpack(fmt, buffer[offset:offset + size])


def iter_unpack(fmt, buffer):
    size = calcsize(fmt)
    if size == 0:
        return
    if isinstance(buffer, (bytearray, memoryview)):
        buffer = bytes(buffer)
    if len(buffer) % size != 0:
        raise ValueError("buffer size not a multiple of struct size")
    for i in range(0, len(buffer), size):
        yield unpack(fmt, buffer[i:i + size])


# ----- Invariant test functions -----

def struct2_pack_unpack():
    try:
        # Big-endian signed int round-trip
        d = pack('>i', 42)
        if unpack('>i', d) != (42,):
            return False
        # Negative signed int
        d = pack('>i', -123456)
        if unpack('>i', d) != (-123456,):
            return False
        # Little-endian unsigned short
        d = pack('<H', 256)
        if d != b'\x00\x01':
            return False
        if unpack('<H', d) != (256,):
            return False
        # Repeat count
        d = pack('>3i', 1, 2, 3)
        if unpack('>3i', d) != (1, 2, 3):
            return False
        # Mixed types
        d = pack('>BHI', 1, 2, 3)
        if unpack('>BHI', d) != (1, 2, 3):
            return False
        # 64-bit
        d = pack('>q', -1)
        if unpack('>q', d) != (-1,):
            return False
        if d != b'\xff\xff\xff\xff\xff\xff\xff\xff':
            return False
        # Unsigned 64-bit
        d = pack('<Q', (1 << 64) - 1)
        if d != b'\xff' * 8:
            return False
        if unpack('<Q', d) != ((1 << 64) - 1,):
            return False
        # bytes string
        d = pack('>4s', b'abc')
        if d != b'abc\x00':
            return False
        if unpack('>4s', d) != (b'abc\x00',):
            return False
        # Boolean
        d = pack('>?', True)
        if unpack('>?', d) != (True,):
            return False
        # Signed byte negative
        d = pack('>b', -5)
        if unpack('>b', d) != (-5,):
            return False
        return True
    except Exception:
        return False


def struct2_calcsize():
    try:
        if calcsize('>i') != 4:
            return False
        if calcsize('<i') != 4:
            return False
        if calcsize('>2i') != 8:
            return False
        if calcsize('>BHI') != 1 + 2 + 4:
            return False
        if calcsize('>q') != 8:
            return False
        if calcsize('>Q') != 8:
            return False
        if calcsize('>b') != 1:
            return False
        if calcsize('>B') != 1:
            return False
        if calcsize('>h') != 2:
            return False
        if calcsize('>H') != 2:
            return False
        if calcsize('>4s') != 4:
            return False
        if calcsize('>10s') != 10:
            return False
        if calcsize('>?') != 1:
            return False
        if calcsize('>3?') != 3:
            return False
        if calcsize('') != 0:
            return False
        if calcsize('>') != 0:
            return False
        # Mix with repeat
        if calcsize('>2H4s') != 2 * 2 + 4:
            return False
        return True
    except Exception:
        return False


def struct2_network_order():
    try:
        # Network order is big-endian
        d = pack('!I', 0x01020304)
        if d != b'\x01\x02\x03\x04':
            return False
        # '>' should match '!'
        if pack('>I', 0x01020304) != b'\x01\x02\x03\x04':
            return False
        # '<' should be reversed
        if pack('<I', 0x01020304) != b'\x04\x03\x02\x01':
            return False
        # Unpack network order
        if unpack('!I', b'\x01\x02\x03\x04') != (0x01020304,):
            return False
        # 16-bit network order
        if pack('!H', 0x1234) != b'\x12\x34':
            return False
        if unpack('!H', b'\x12\x34') != (0x1234,):
            return False
        # 64-bit network order
        if pack('!Q', 0x0102030405060708) != b'\x01\x02\x03\x04\x05\x06\x07\x08':
            return False
        if unpack('!Q', b'\x01\x02\x03\x04\x05\x06\x07\x08') != (0x0102030405060708,):
            return False
        # Round-trip large network value
        v = 0xDEADBEEF
        if unpack('!I', pack('!I', v)) != (v,):
            return False
        # Network differs from little for non-symmetric values
        if pack('!H', 0x00FF) == pack('<H', 0x00FF):
            return False
        return True
    except Exception:
        return False