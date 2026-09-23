# generation A date class

_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap_year(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False


def _days_in_month(year, month):
    if month == 2 and _is_leap_year(year):
        return 29
    return _DAYS_IN_MONTH[month - 1]


class date(object):
    __slots__ = ("year", "month", "day")

    def __init__(self, year, month, day):
        if month < 1 or month > 12:
            raise ValueError("month must be in 1..12")
        last = _days_in_month(year, month)
        if day < 1 or day > last:
            raise ValueError("day is out of range for month")
        self.year = year
        self.month = month
        self.day = day

    def isoformat(self):
        return "%04d-%02d-%02d" % (self.year, self.month, self.day)
