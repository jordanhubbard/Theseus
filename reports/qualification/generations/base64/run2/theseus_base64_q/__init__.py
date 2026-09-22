# generation B integer groups

_B64_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B32_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_HEX_ALPHABET = b"0123456789ABCDEF"
_ASCII_WHITESPACE = {9, 10, 11, 12, 13, 32}


def _bytes_input(value, name):
    if isinstance(value, bytes):
        return value
    try:
        return memoryview(value).tobytes()
    except TypeError:
        raise TypeError("%s must be a bytes-like object" % name)


def _decode_input(value):
    if isinstance(value, str):
        try:
            return value.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("string argument should contain only ASCII characters")
    return _bytes_input(value, "s")


def _altchars(value):
    result = _bytes_input(value, "altchars")
    if len(result) != 2:
        raise ValueError("altchars must contain exactly two bytes")
    return result


def b64encode(s, altchars=None):
    data = _bytes_input(s, "s")
    alphabet = _B64_ALPHABET
    if altchars is not None:
        alternate = _altchars(altchars)
        alphabet = alphabet[:62] + alternate

    output = bytearray()
    for position in range(0, len(data), 3):
        group = data[position:position + 3]
        size = len(group)
        value = group[0] << 16
        if size > 1:
            value |= group[1] << 8
        if size > 2:
            value |= group[2]

        output.append(alphabet[(value >> 18) & 63])
        output.append(alphabet[(value >> 12) & 63])
        output.append(alphabet[(value >> 6) & 63] if size > 1 else 61)
        output.append(alphabet[value & 63] if size > 2 else 61)
    return bytes(output)


def b64decode(s, altchars=None, validate=False):
    data = _decode_input(s)
    reverse = [-1] * 256
    for index, byte in enumerate(_B64_ALPHABET):
        reverse[byte] = index

    if altchars is not None:
        alternate = _altchars(altchars)
        reverse[alternate[0]] = 62
        reverse[alternate[1]] = 63

    cleaned = bytearray()
    for byte in data:
        if reverse[byte] >= 0 or byte == 61:
            cleaned.append(byte)
        elif byte in _ASCII_WHITESPACE:
            continue
        elif validate:
            raise ValueError("non-alphabet character found")

    if not cleaned:
        return b""
    if len(cleaned) % 4:
        raise ValueError("incorrect padding")

    first_padding = cleaned.find(61)
    if first_padding < 0:
        padding = 0
        data_length = len(cleaned)
    else:
        padding = len(cleaned) - first_padding
        data_length = first_padding
        if padding > 2 or any(byte != 61 for byte in cleaned[first_padding:]):
            raise ValueError("incorrect padding")

    remainder = data_length % 4
    if remainder == 1:
        raise ValueError("incorrect padding")
    required_padding = 0 if remainder == 0 else 4 - remainder
    if padding != required_padding:
        raise ValueError("incorrect padding")

    output = bytearray()
    for position in range(0, len(cleaned), 4):
        group = cleaned[position:position + 4]
        values = []
        for byte in group:
            values.append(0 if byte == 61 else reverse[byte])
        value = (
            (values[0] << 18)
            | (values[1] << 12)
            | (values[2] << 6)
            | values[3]
        )
        output.append((value >> 16) & 255)
        if group[2] != 61:
            output.append((value >> 8) & 255)
        if group[3] != 61:
            output.append(value & 255)
    return bytes(output)


def urlsafe_b64encode(s):
    return b64encode(s, b"-_")


def urlsafe_b64decode(s):
    return b64decode(s, b"-_")


def b32encode(s):
    data = _bytes_input(s, "s")
    output = bytearray()
    for position in range(0, len(data), 5):
        group = data[position:position + 5]
        size = len(group)
        value = 0
        for byte in group:
            value = (value << 8) | byte
        value <<= (5 - size) * 8

        encoded_count = (size * 8 + 4) // 5
        for shift in range(35, -1, -5):
            if len(output) % 8 < encoded_count:
                output.append(_B32_ALPHABET[(value >> shift) & 31])
            else:
                output.append(61)
    return bytes(output)


def b16encode(s):
    data = _bytes_input(s, "s")
    output = bytearray()
    for byte in data:
        output.append(_HEX_ALPHABET[byte >> 4])
        output.append(_HEX_ALPHABET[byte & 15])
    return bytes(output)
