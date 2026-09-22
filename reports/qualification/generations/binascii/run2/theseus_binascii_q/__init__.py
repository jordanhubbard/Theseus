# generation B crc bits


class Error(ValueError):
    pass


def crc32(data, value=0):
    crc = (value & 0xFFFFFFFF) ^ 0xFFFFFFFF
    for byte in memoryview(data).cast("B"):
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def hexlify(data, sep=None, bytes_per_sep=1):
    digits = b"0123456789abcdef"
    raw = bytes(memoryview(data).cast("B"))
    encoded = bytearray(len(raw) * 2)
    position = 0
    for byte in raw:
        encoded[position] = digits[byte >> 4]
        encoded[position + 1] = digits[byte & 15]
        position += 2

    if sep is None:
        return bytes(encoded)
    if isinstance(sep, str):
        separator = sep.encode("ascii")
    else:
        separator = bytes(sep)
    if len(separator) != 1:
        raise ValueError("sep must be length 1")
    if bytes_per_sep == 0:
        return bytes(encoded)

    group_size = abs(bytes_per_sep)
    groups = []
    if bytes_per_sep > 0:
        first_size = len(raw) % group_size
        if first_size:
            groups.append(bytes(encoded[:first_size * 2]))
        start = first_size
    else:
        start = 0
    while start < len(raw):
        end = min(start + group_size, len(raw))
        groups.append(bytes(encoded[start * 2:end * 2]))
        start = end
    return separator.join(groups)


def unhexlify(hexstr):
    if isinstance(hexstr, str):
        try:
            raw = hexstr.encode("ascii")
        except UnicodeEncodeError:
            raise Error("Non-hexadecimal digit found")
    else:
        raw = bytes(hexstr)
    if len(raw) % 2:
        raise Error("Odd-length string")

    result = bytearray(len(raw) // 2)
    for index in range(0, len(raw), 2):
        high = _hex_value(raw[index])
        low = _hex_value(raw[index + 1])
        if high < 0 or low < 0:
            raise Error("Non-hexadecimal digit found")
        result[index // 2] = (high << 4) | low
    return bytes(result)


def _hex_value(byte):
    if 48 <= byte <= 57:
        return byte - 48
    if 65 <= byte <= 70:
        return byte - 55
    if 97 <= byte <= 102:
        return byte - 87
    return -1
