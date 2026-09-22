# generation B quoted-printable class


class _QuotedPrintable:
    _HEX = b"0123456789ABCDEF"

    @staticmethod
    def _bytes(value):
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode("ascii")
        return bytes(value)

    def _quoted(self, value):
        return bytes((61, self._HEX[value >> 4], self._HEX[value & 15]))

    @staticmethod
    def _hex_value(value):
        if 48 <= value <= 57:
            return value - 48
        if 65 <= value <= 70:
            return value - 55
        if 97 <= value <= 102:
            return value - 87
        return -1

    def _token(self, value, quote_whitespace, header, trailing):
        if header and value == 32 and not trailing:
            return b"_"
        if (
            33 <= value <= 126
            and value != 61
            and not (header and value == 95)
        ):
            return bytes((value,))
        if value in (9, 32) and not quote_whitespace and not trailing:
            return bytes((value,))
        return self._quoted(value)

    def _encode_line(self, body, newline, quotetabs, header):
        if body == b".":
            tokens = [b"=2E"]
        else:
            last = len(body) - 1
            tokens = [
                self._token(
                    value,
                    quotetabs,
                    header,
                    index == last and value in (9, 32),
                )
                for index, value in enumerate(body)
            ]

        result = bytearray()
        current = bytearray()
        final_index = len(tokens) - 1
        soft_newline = newline or b"\n"
        for index, token in enumerate(tokens):
            limit = 76 if index == final_index else 75
            if current and len(current) + len(token) > limit:
                result.extend(current)
                result.extend(b"=")
                result.extend(soft_newline)
                current = bytearray()
            current.extend(token)
        result.extend(current)
        result.extend(newline)
        return bytes(result)

    def encodestring(self, value, quotetabs=False, header=False):
        data = self._bytes(value)
        result = bytearray()
        start = 0
        while start < len(data):
            end = data.find(b"\n", start)
            if end < 0:
                result.extend(
                    self._encode_line(data[start:], b"", quotetabs, header)
                )
                break
            if end > start and data[end - 1] == 13:
                body = data[start : end - 1]
                newline = b"\r\n"
            else:
                body = data[start:end]
                newline = b"\n"
            result.extend(self._encode_line(body, newline, quotetabs, header))
            start = end + 1
        return bytes(result)

    def decodestring(self, value, header=False):
        data = self._bytes(value)
        result = bytearray()
        index = 0
        size = len(data)
        while index < size:
            value = data[index]
            if header and value == 95:
                result.append(32)
                index += 1
                continue
            if value != 61:
                result.append(value)
                index += 1
                continue
            if index + 1 < size and data[index + 1] == 10:
                index += 2
                continue
            if (
                index + 2 < size
                and data[index + 1] == 13
                and data[index + 2] == 10
            ):
                index += 3
                continue
            if index + 2 < size:
                high = self._hex_value(data[index + 1])
                low = self._hex_value(data[index + 2])
                if high >= 0 and low >= 0:
                    result.append((high << 4) | low)
                    index += 3
                    continue
            if index + 1 == size:
                index += 1
                continue
            result.append(61)
            index += 1
        return bytes(result)

    def encode(self, input_file, output_file, quotetabs, header=False):
        output_file.write(
            self.encodestring(input_file.read(), quotetabs=quotetabs, header=header)
        )

    def decode(self, input_file, output_file, header=False):
        output_file.write(self.decodestring(input_file.read(), header=header))


_codec = _QuotedPrintable()


def encodestring(value, quotetabs=False, header=False):
    return _codec.encodestring(value, quotetabs=quotetabs, header=header)


def decodestring(value, header=False):
    return _codec.decodestring(value, header=header)


def encode(input_file, output_file, quotetabs, header=False):
    return _codec.encode(input_file, output_file, quotetabs, header=header)


def decode(input_file, output_file, header=False):
    return _codec.decode(input_file, output_file, header=header)
