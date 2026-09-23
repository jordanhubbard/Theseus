# generation B date factory


def _as_integer(value):
    try:
        result = value.__index__()
    except AttributeError:
        raise TypeError(
            "'%s' object cannot be interpreted as an integer"
            % type(value).__name__
        )
    if not isinstance(result, int):
        raise TypeError("__index__ returned non-int")
    return result


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


class _Date:
    __slots__ = ("_year", "_month", "_day")

    def __init__(self, year, month, day):
        year = _as_integer(year)
        month = _as_integer(month)
        day = _as_integer(day)

        if year < 1 or year > 9999:
            raise ValueError("year must be in 1..9999")
        if month < 1 or month > 12:
            raise ValueError("month must be in 1..12")

        month_lengths = (31, 29 if _is_leap(year) else 28, 31, 30, 31, 30,
                         31, 31, 30, 31, 30, 31)
        if day < 1 or day > month_lengths[month - 1]:
            raise ValueError("day is out of range for month")

        self._year = year
        self._month = month
        self._day = day

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def day(self):
        return self._day

    def isoformat(self):
        return "%04d-%02d-%02d" % (self._year, self._month, self._day)

    def __str__(self):
        return self.isoformat()

    def __repr__(self):
        return "theseus_datetime_q.date(%d, %d, %d)" % (
            self._year,
            self._month,
            self._day,
        )

    def __eq__(self, other):
        if not isinstance(other, _Date):
            return NotImplemented
        return (
            self._year == other._year
            and self._month == other._month
            and self._day == other._day
        )

    def __hash__(self):
        return hash((self._year, self._month, self._day))


def date(year, month, day):
    return _Date(year, month, day)


__all__ = ["date"]
