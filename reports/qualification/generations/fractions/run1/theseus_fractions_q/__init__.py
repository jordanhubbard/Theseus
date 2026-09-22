# generation A fraction reduce

import math


def _gcd_pair(numerator, denominator):
    return math.gcd(abs(numerator), abs(denominator))


def _normalize(numerator, denominator):
    if denominator == 0:
        raise ZeroDivisionError("Fraction(1, 0)")
    if numerator == 0:
        return 0, 1
    if denominator < 0:
        numerator = -numerator
        denominator = -denominator
    g = _gcd_pair(numerator, denominator)
    return numerator // g, denominator // g


def _parse_ratio(text):
    text = text.strip()
    if not text:
        raise ValueError("Invalid literal for Fraction: %r" % (text,))
    if "/" in text:
        left, right = text.split("/", 1)
        if not left or not right:
            raise ValueError("Invalid literal for Fraction: %r" % (text,))
        numerator = int(left.strip())
        denominator = int(right.strip())
    else:
        numerator = int(text)
        denominator = 1
    return _normalize(numerator, denominator)


class Fraction(object):
    __slots__ = ("_numerator", "_denominator")

    def __new__(cls, numerator=0, denominator=None):
        if denominator is None:
            if isinstance(numerator, str):
                num, den = _parse_ratio(numerator)
            elif isinstance(numerator, int):
                num, den = _normalize(numerator, 1)
            else:
                raise TypeError(
                    "argument should be a string or a rational number"
                )
        else:
            if isinstance(numerator, str) or isinstance(denominator, str):
                raise TypeError("both arguments should be integers")
            num, den = _normalize(int(numerator), int(denominator))
        self = super(Fraction, cls).__new__(cls)
        self._numerator = num
        self._denominator = den
        return self

    def __str__(self):
        if self._denominator == 1:
            return str(self._numerator)
        return "%d/%d" % (self._numerator, self._denominator)

    def __repr__(self):
        return "Fraction(%d, %d)" % (self._numerator, self._denominator)


__all__ = ["Fraction"]
