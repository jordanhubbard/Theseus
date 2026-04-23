"""
theseus_struct: Clean-room implementation of binary pack/unpack.
"""

# Format character definitions: (size_in_bytes, signed)
_FORMAT_CHARS = {
    'B': (1, False),
    'H': (2, False),
    'I': (4, False),
    'i': (4, True),
    'h': (2, True),
    'b': (1, True),
    'Q': (8, False),
    'q': (8, True),
}


def _parse_fmt(fmt: str):
    if not fmt:
        raise ValueError("Empty format string")

    if fmt[0] == '>':
        endian = 'big'
        chars = fmt[1:]
    elif fmt[0] == '<':
        endian = 'little'
        chars = fmt[1:]
    else:
        endian = 'big'
        chars = fmt

    parsed = []
    for ch in chars:
        if ch not in _FORMAT_CHARS:
            raise ValueError(f"Unsupported format character: '{ch}'")
        parsed.append(ch)

    return endian, parsed


def _int_to_bytes(value: int, size: int, endian: str, signed: bool) -> bytes:
    if signed:
        if value < 0:
            value = value + (1 << (size * 8))
        max_val = (1 << (size * 8)) - 1
        if value < 0 or value > max_val:
            raise ValueError(f"Value out of range for signed {size}-byte integer")
    else:
        if value < 0:
            raise ValueError(f"Value {value} is negative but format is unsigned")
        max_val = (1 << (size * 8)) - 1
        if value > max_val:
            raise ValueError(f"Value {value} out of range for unsigned {size}-byte integer")

    result = []
    for _ in range(size):
        result.append(value & 0xFF)
        value >>= 8

    if endian == 'big':
        result.reverse()

    return bytes(result)


def _bytes_to_int(data: bytes, offset: int, size: int, endian: str, signed: bool) -> int:
    chunk = data[offset:offset + size]
    if len(chunk) != size:
        raise ValueError(f"Not enough data: expected {size} bytes, got {len(chunk)}")

    if endian == 'big':
        value = 0
        for byte in chunk:
            value = (value << 8) | byte
    else:
        value = 0
        for i, byte in enumerate(chunk):
            value |= byte << (8 * i)

    if signed:
        if value >= (1 << (size * 8 - 1)):
            value -= (1 << (size * 8))

    return value


def pack(fmt: str, *args) -> bytes:
    """
    Pack values into bytes according to the format string.

    Format prefix:
        '>' - big-endian
        '<' - little-endian

    Format characters:
        'B' - unsigned byte (1 byte)
        'b' - signed byte (1 byte)
        'H' - unsigned short (2 bytes)
        'h' - signed short (2 bytes)
        'I' - unsigned int (4 bytes)
        'i' - signed int (4 bytes)
        'Q' - unsigned long long (8 bytes)
        'q' - signed long long (8 bytes)
    """
    endian, parsed = _parse_fmt(fmt)

    if len(parsed) != len(args):
        raise ValueError(
            f"pack expected {len(parsed)} items for packing, got {len(args)}"
        )

    result = bytearray()
    for ch, value in zip(parsed, args):
        size, signed = _FORMAT_CHARS[ch]
        result.extend(_int_to_bytes(int(value), size, endian, signed))

    return bytes(result)


def unpack(fmt: str, data: bytes) -> tuple:
    """
    Unpack bytes into values according to the format string.

    Format prefix:
        '>' - big-endian
        '<' - little-endian

    Format characters:
        'B' - unsigned byte (1 byte)
        'b' - signed byte (1 byte)
        'H' - unsigned short (2 bytes)
        'h' - signed short (2 bytes)
        'I' - unsigned int (4 bytes)
        'i' - signed int (4 bytes)
        'Q' - unsigned long long (8 bytes)
        'q' - signed long long (8 bytes)
    """
    endian, parsed = _parse_fmt(fmt)

    expected_size = sum(_FORMAT_CHARS[ch][0] for ch in parsed)
    if len(data) < expected_size:
        raise ValueError(
            f"unpack requires a buffer of {expected_size} bytes, got {len(data)}"
        )

    result = []
    offset = 0
    for ch in parsed:
        size, signed = _FORMAT_CHARS[ch]
        value = _bytes_to_int(data, offset, size, endian, signed)
        result.append(value)
        offset += size

    return tuple(result)


def struct_pack_big_endian() -> bool:
    return pack('>I', 256) == b'\x00\x00\x01\x00'


def struct_unpack_big_endian() -> bool:
    return unpack('>I', b'\x00\x00\x01\x00') == (256,)


def struct_pack_little_endian() -> bool:
    return pack('<H', 1) == b'\x01\x00'


def calcsize(fmt: str) -> int:
    """Return the size in bytes of the packed format string."""
    _, parsed = _parse_fmt(fmt)
    return sum(_FORMAT_CHARS[ch][0] for ch in parsed)