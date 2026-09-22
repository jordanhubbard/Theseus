# generation B ratio factory

from math import gcd


class _Ratio:
    """A reduced rational value with a positive denominator."""

    __slots__ = ("_numerator", "_denominator")

    def __init__(self, numerator=0, denominator=None):
        if denominator is None:
            if isinstance(numerator, _Ratio):
                top = numerator.numerator
                bottom = numerator.denominator
            elif isinstance(numerator, int):
                top = numerator
                bottom = 1
            elif isinstance(numerator, str):
                top, bottom = self._parse(numerator)
            else:
                raise TypeError(
                    "argument should be an integer, ratio string, or _Ratio"
                )
        else:
            if not isinstance(numerator, int) or not isinstance(denominator, int):
                raise TypeError("both arguments should be integers")
            top = numerator
            bottom = denominator

        if bottom == 0:
            raise ZeroDivisionError("Fraction denominator cannot be zero")

        common = gcd(top, bottom)
        top //= common
        bottom //= common
        if bottom < 0:
            top = -top
            bottom = -bottom

        self._numerator = top
        self._denominator = bottom

    @staticmethod
    def _parse(value):
        text = value.strip()
        if not text or any(character.isspace() for character in text):
            raise ValueError("Invalid literal for Fraction: {!r}".format(value))

        if text.count("/") > 1:
            raise ValueError("Invalid literal for Fraction: {!r}".format(value))

        if "/" in text:
            top_text, bottom_text = text.split("/")
        else:
            top_text, bottom_text = text, "1"

        try:
            top = int(top_text, 10)
            bottom = int(bottom_text, 10)
        except ValueError:
            raise ValueError(
                "Invalid literal for Fraction: {!r}".format(value)
            ) from None
        return top, bottom

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator

    def __str__(self):
        if self.denominator == 1:
            return str(self.numerator)
        return "{}/{}".format(self.numerator, self.denominator)

    def __repr__(self):
        return "Fraction({}, {})".format(self.numerator, self.denominator)

    def __eq__(self, other):
        if isinstance(other, _Ratio):
            return (
                self.numerator == other.numerator
                and self.denominator == other.denominator
            )
        if isinstance(other, int):
            return self.denominator == 1 and self.numerator == other
        return NotImplemented

    def __hash__(self):
        return hash((self.numerator, self.denominator))


def Fraction(numerator=0, denominator=None):
    """Create a reduced rational number from integers or a ratio string."""
    return _Ratio(numerator, denominator)


__all__ = ["Fraction"]
