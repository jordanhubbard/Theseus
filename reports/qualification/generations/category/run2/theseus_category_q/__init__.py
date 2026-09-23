# generation B category class


class _Cat:
    def category(self, character):
        if not isinstance(character, str) or len(character) != 1:
            raise TypeError("category() argument must be a unicode character")
        if "A" <= character <= "Z":
            return "Lu"
        if "a" <= character <= "z":
            return "Ll"
        if "0" <= character <= "9":
            return "Nd"
        raise ValueError("character category is outside the supported scope")


_cat = _Cat()


def category(character):
    return _cat.category(character)
