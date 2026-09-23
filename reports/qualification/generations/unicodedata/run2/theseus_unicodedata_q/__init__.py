# generation B name class


class _Names:
    def lookup(self, character):
        if not isinstance(character, str) or len(character) != 1:
            raise TypeError("name() argument must be a single character")
        if "A" <= character <= "Z":
            return "LATIN CAPITAL LETTER " + character
        raise ValueError("no such name")


_NAMES = _Names()


def name(character):
    return _NAMES.lookup(character)
