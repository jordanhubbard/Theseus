# generation B gregorian class


class _Gregorian:
    _MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    _DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

    def isleap(self, year):
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def weekday(self, year, month, day):
        if not 1 <= month <= 12:
            raise ValueError("month must be in 1..12")

        month_length = self._MONTH_LENGTHS[month - 1]
        if month == 2 and self.isleap(year):
            month_length += 1
        if not 1 <= day <= month_length:
            raise ValueError("day is out of range for month")

        prior_year = year - 1
        days = (
            365 * prior_year
            + prior_year // 4
            - prior_year // 100
            + prior_year // 400
            + self._DAYS_BEFORE_MONTH[month - 1]
            + day
            - 1
        )
        if month > 2 and self.isleap(year):
            days += 1
        return int(days % 7)

    def leapdays(self, y1, y2):
        end = y2 - 1
        start = y1 - 1
        return (
            end // 4
            - end // 100
            + end // 400
            - start // 4
            + start // 100
            - start // 400
        )

    def monthrange(self, year, month):
        if not 1 <= month <= 12:
            raise ValueError("month must be in 1..12")
        days = self._MONTH_LENGTHS[month - 1]
        if month == 2 and self.isleap(year):
            days += 1
        return self.weekday(year, month, 1), days


_GREGORIAN = _Gregorian()


def isleap(year):
    return _GREGORIAN.isleap(year)


def weekday(year, month, day):
    return _GREGORIAN.weekday(year, month, day)


def leapdays(y1, y2):
    return _GREGORIAN.leapdays(y1, y2)


def monthrange(year, month):
    return _GREGORIAN.monthrange(year, month)
