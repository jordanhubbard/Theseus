# generation B rot13 class


class _Rot13:
    def encode(self, text):
        result = []
        for character in text:
            codepoint = ord(character)
            if 65 <= codepoint <= 90:
                codepoint = 65 + ((codepoint - 65 + 13) % 26)
                result.append(chr(codepoint))
            elif 97 <= codepoint <= 122:
                codepoint = 97 + ((codepoint - 97 + 13) % 26)
                result.append(chr(codepoint))
            else:
                result.append(character)
        return "".join(result)


def encode(text, encoding):
    if encoding != "rot_13":
        raise LookupError("unknown encoding: " + encoding)
    return _Rot13().encode(text)
