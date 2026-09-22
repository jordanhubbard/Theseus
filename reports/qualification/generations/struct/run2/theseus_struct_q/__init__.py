# generation B format tokens
import math
import operator
import sys


class error(Exception):
    pass


_SIZES = {
    "x": 1,
    "c": 1,
    "b": 1,
    "B": 1,
    "?": 1,
    "h": 2,
    "H": 2,
    "i": 4,
    "I": 4,
    "l": 4,
    "L": 4,
    "q": 8,
    "Q": 8,
    "e": 2,
    "f": 4,
    "d": 8,
    "s": 1,
}

_INTEGER_CODES = {
    "b": (1, True),
    "B": (1, False),
    "h": (2, True),
    "H": (2, False),
    "i": (4, True),
    "I": (4, False),
    "l": (4, True),
    "L": (4, False),
    "q": (8, True),
    "Q": (8, False),
}

_FLOAT_CODES = {
    "e": (5, 10),
    "f": (8, 23),
    "d": (11, 52),
}


def _format_text(fmt):
    if isinstance(fmt, bytes):
        try:
            return fmt.decode("ascii")
        except UnicodeDecodeError:
            raise error("bad char in struct format")
    if not isinstance(fmt, str):
        raise TypeError("Struct() argument 1 must be a str or bytes object")
    return fmt


def _tokens(fmt):
    text = _format_text(fmt)
    endian = sys.byteorder
    position = 0
    if text and text[0] in "<>!=":
        prefix = text[0]
        position = 1
        if prefix in ">!":
            endian = "big"
        elif prefix == "<":
            endian = "little"
        else:
            endian = sys.byteorder

    result = []
    length = len(text)
    while position < length:
        if text[position].isspace():
            position += 1
            continue
        count = 0
        has_count = False
        while position < length and text[position].isdigit():
            has_count = True
            count = count * 10 + ord(text[position]) - ord("0")
            position += 1
        if position >= length:
            raise error("repeat count given without format specifier")
        code = text[position]
        position += 1
        if code.isspace():
            raise error("bad char in struct format")
        if code not in _SIZES:
            raise error("bad char in struct format")
        if not has_count:
            count = 1
        result.append((code, count, endian))
    return result


def calcsize(fmt):
    total = 0
    for code, count, unused_endian in _tokens(fmt):
        total += _SIZES[code] * count
    return total


def _integer_bytes(value, size, signed, endian, code):
    try:
        number = operator.index(value)
    except TypeError:
        raise error("required argument is not an integer")
    bits = size * 8
    if signed:
        minimum = -(1 << (bits - 1))
        maximum = (1 << (bits - 1)) - 1
    else:
        minimum = 0
        maximum = (1 << bits) - 1
    if number < minimum or number > maximum:
        raise error("%s format requires a value in range" % code)
    return number.to_bytes(size, endian, signed=signed)


def _float_bits(value, exponent_bits, fraction_bits):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise error("required argument is not a float")
    sign = 1 if math.copysign(1.0, number) < 0.0 else 0
    magnitude = abs(number)
    maximum_exponent = (1 << exponent_bits) - 1
    bias = (1 << (exponent_bits - 1)) - 1

    if math.isnan(magnitude):
        exponent = maximum_exponent
        fraction = 1 << (fraction_bits - 1)
    elif math.isinf(magnitude):
        exponent = maximum_exponent
        fraction = 0
    elif magnitude == 0.0:
        exponent = 0
        fraction = 0
    else:
        significand, power = math.frexp(magnitude)
        unbiased = power - 1
        if unbiased > bias:
            raise OverflowError("float too large to pack")
        if unbiased >= 1 - bias:
            exponent = unbiased + bias
            fraction = round(math.ldexp(significand, fraction_bits + 1)) - (
                1 << fraction_bits
            )
            if fraction == (1 << fraction_bits):
                fraction = 0
                exponent += 1
                if exponent >= maximum_exponent:
                    raise OverflowError("float too large to pack")
        else:
            exponent = 0
            fraction = round(
                math.ldexp(magnitude, bias - 1 + fraction_bits)
            )
            if fraction == (1 << fraction_bits):
                exponent = 1
                fraction = 0

    return (
        (sign << (exponent_bits + fraction_bits))
        | (exponent << fraction_bits)
        | fraction
    )


def _float_bytes(value, code, endian):
    exponent_bits, fraction_bits = _FLOAT_CODES[code]
    bits = _float_bits(value, exponent_bits, fraction_bits)
    return bits.to_bytes(_SIZES[code], endian)


def pack(fmt, *values):
    tokens = _tokens(fmt)
    output = bytearray()
    value_position = 0

    for code, count, endian in tokens:
        if code == "x":
            output.extend(b"\x00" * count)
        elif code == "s":
            if value_position >= len(values):
                raise error("pack expected more items for packing")
            value = values[value_position]
            value_position += 1
            if not isinstance(value, (bytes, bytearray)):
                raise error("argument for 's' must be a bytes object")
            raw = bytes(value)
            output.extend(raw[:count])
            if len(raw) < count:
                output.extend(b"\x00" * (count - len(raw)))
        else:
            for unused_index in range(count):
                if value_position >= len(values):
                    raise error("pack expected more items for packing")
                value = values[value_position]
                value_position += 1
                if code == "c":
                    if not isinstance(value, (bytes, bytearray)) or len(value) != 1:
                        raise error("char format requires a bytes object of length 1")
                    output.extend(value)
                elif code == "?":
                    output.append(1 if value else 0)
                elif code in _INTEGER_CODES:
                    size, signed = _INTEGER_CODES[code]
                    output.extend(_integer_bytes(value, size, signed, endian, code))
                else:
                    output.extend(_float_bytes(value, code, endian))

    if value_position != len(values):
        raise error(
            "pack expected %d items for packing (got %d)"
            % (value_position, len(values))
        )
    return bytes(output)


def _float_from_bits(bits, exponent_bits, fraction_bits):
    sign_shift = exponent_bits + fraction_bits
    sign = -1.0 if (bits >> sign_shift) else 1.0
    exponent_mask = (1 << exponent_bits) - 1
    fraction_mask = (1 << fraction_bits) - 1
    exponent = (bits >> fraction_bits) & exponent_mask
    fraction = bits & fraction_mask
    bias = (1 << (exponent_bits - 1)) - 1

    if exponent == exponent_mask:
        if fraction:
            return float("nan")
        return sign * float("inf")
    if exponent == 0:
        if fraction == 0:
            return math.copysign(0.0, sign)
        value = math.ldexp(float(fraction), 1 - bias - fraction_bits)
    else:
        value = math.ldexp(
            1.0 + float(fraction) / (1 << fraction_bits),
            exponent - bias,
        )
    return sign * value


def unpack(fmt, buffer):
    tokens = _tokens(fmt)
    try:
        data = bytes(buffer)
    except (TypeError, ValueError):
        raise TypeError("a bytes-like object is required")
    expected = 0
    for code, count, unused_endian in tokens:
        expected += _SIZES[code] * count
    if len(data) != expected:
        raise error("unpack requires a buffer of %d bytes" % expected)

    values = []
    position = 0
    for code, count, endian in tokens:
        if code == "x":
            position += count
        elif code == "s":
            values.append(data[position:position + count])
            position += count
        else:
            size = _SIZES[code]
            for unused_index in range(count):
                raw = data[position:position + size]
                position += size
                if code == "c":
                    values.append(raw)
                elif code == "?":
                    values.append(raw[0] != 0)
                elif code in _INTEGER_CODES:
                    unused_size, signed = _INTEGER_CODES[code]
                    values.append(int.from_bytes(raw, endian, signed=signed))
                else:
                    exponent_bits, fraction_bits = _FLOAT_CODES[code]
                    bits = int.from_bytes(raw, endian)
                    values.append(
                        _float_from_bits(bits, exponent_bits, fraction_bits)
                    )
    return tuple(values)
