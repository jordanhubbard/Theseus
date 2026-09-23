# generation A decimal text


class Decimal(object):
    """Decimal values built from numeric strings; str keeps written coefficients."""

    __slots__ = ("_text",)

    _SPECIALS = {
        "infinity": "Infinity",
        "inf": "Infinity",
        "+infinity": "Infinity",
        "+inf": "Infinity",
        "-infinity": "-Infinity",
        "-inf": "-Infinity",
        "nan": "NaN",
        "+nan": "NaN",
        "-nan": "NaN",
        "snan": "sNaN",
        "+snan": "sNaN",
        "-snan": "-sNaN",
    }

    def __init__(self, value="0"):
        if isinstance(value, Decimal):
            self._text = value._text
            return
        if not isinstance(value, str):
            raise TypeError(
                "conversion from %s to Decimal is not supported"
                % type(value).__name__
            )
        self._text = self._from_string(value)

    @classmethod
    def _from_string(cls, value):
        raw = value.strip()
        if not raw:
            raise ValueError("invalid literal for Decimal: %r" % (value,))

        key = raw.lower()
        if key in cls._SPECIALS:
            return cls._SPECIALS[key]

        sign = ""
        body = raw
        if body[0] in "+-":
            if body[0] == "-":
                sign = "-"
            body = body[1:].lstrip()
            if not body:
                raise ValueError("invalid literal for Decimal: %r" % (value,))

        if "e" in body or "E" in body:
            raise ValueError("invalid literal for Decimal: %r" % (value,))

        if "." in body:
            left, right = body.split(".", 1)
            if left == "" and right == "":
                raise ValueError("invalid literal for Decimal: %r" % (value,))
            if left != "" and not left.isdigit():
                raise ValueError("invalid literal for Decimal: %r" % (value,))
            if right != "" and not right.isdigit():
                raise ValueError("invalid literal for Decimal: %r" % (value,))
            int_part = left
            frac_part = right
            has_dot = True
        else:
            if not body.isdigit():
                raise ValueError("invalid literal for Decimal: %r" % (value,))
            int_part = body
            frac_part = ""
            has_dot = False

        if int_part == "":
            int_digits = "0"
        else:
            int_digits = int_part.lstrip("0")
            if int_digits == "":
                int_digits = "0"

        if not has_dot:
            text = int_digits
        elif frac_part == "":
            text = int_digits
        else:
            text = int_digits + "." + frac_part

        if sign == "-":
            if text == "0" or (has_dot and frac_part != "" and int_digits == "0" and set(frac_part) <= {"0"}):
                if has_dot and frac_part != "":
                    text = "-0." + frac_part
                else:
                    text = "-0"
            else:
                text = "-" + text

        return text

    def __str__(self):
        return self._text

    def __repr__(self):
        return "Decimal('%s')" % self._text
