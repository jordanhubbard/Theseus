# generation B escape class


class _Escaper:
    @staticmethod
    def _is_safe(character):
        return (
            "a" <= character <= "z"
            or "A" <= character <= "Z"
            or "0" <= character <= "9"
            or character == "_"
        )

    def escape(self, pattern):
        return "".join(
            character if self._is_safe(character) else "\\" + character
            for character in pattern
        )


def escape(pattern):
    return _Escaper().escape(pattern)
