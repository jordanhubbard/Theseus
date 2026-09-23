# generation B decimal class


class _Decimal:
    """Minimal exact textual decimal value."""

    __slots__ = ("_coefficient",)

    def __init__(self, text):
        if not isinstance(text, str):
            raise TypeError("Decimal requires a string")
        self._coefficient = text

    def __str__(self):
        return self._coefficient


def Decimal(text):
    return _Decimal(text)
