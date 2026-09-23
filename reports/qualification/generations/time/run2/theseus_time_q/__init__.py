# generation B epoch class


class _Clock:
    class Record(tuple):
        __slots__ = ()

        def __new__(
            cls,
            year,
            month,
            day,
            hour,
            minute,
            second,
            weekday,
            yearday,
            isdst,
        ):
            return tuple.__new__(
                cls,
                (
                    year,
                    month,
                    day,
                    hour,
                    minute,
                    second,
                    weekday,
                    yearday,
                    isdst,
                ),
            )

        tm_year = property(lambda self: self[0])
        tm_mon = property(lambda self: self[1])
        tm_mday = property(lambda self: self[2])
        tm_hour = property(lambda self: self[3])
        tm_min = property(lambda self: self[4])
        tm_sec = property(lambda self: self[5])
        tm_wday = property(lambda self: self[6])
        tm_yday = property(lambda self: self[7])
        tm_isdst = property(lambda self: self[8])

    @staticmethod
    def _is_leap(year):
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    @classmethod
    def _civil_date(cls, days):
        shifted = days + 719468
        era = shifted // 146097
        day_of_era = shifted - era * 146097
        year_of_era = (
            day_of_era
            - day_of_era // 1460
            + day_of_era // 36524
            - day_of_era // 146096
        ) // 365
        year = year_of_era + era * 400
        day_of_year = day_of_era - (
            365 * year_of_era + year_of_era // 4 - year_of_era // 100
        )
        month_phase = (5 * day_of_year + 2) // 153
        day = day_of_year - (153 * month_phase + 2) // 5 + 1
        month = month_phase + 3 if month_phase < 10 else month_phase - 9
        year += 1 if month <= 2 else 0
        return year, month, day

    @classmethod
    def _year_day(cls, year, month, day):
        starts = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
        result = starts[month - 1] + day
        if month > 2 and cls._is_leap(year):
            result += 1
        return result

    @classmethod
    def convert(cls, seconds):
        whole_seconds = int(seconds // 1)
        days, within_day = divmod(whole_seconds, 86400)
        hour, within_hour = divmod(within_day, 3600)
        minute, second = divmod(within_hour, 60)
        year, month, day = cls._civil_date(days)
        weekday = (days + 3) % 7
        return cls.Record(
            year,
            month,
            day,
            hour,
            minute,
            second,
            weekday,
            cls._year_day(year, month, day),
            0,
        )


_CLOCK = _Clock()


def gmtime(seconds):
    return _CLOCK.convert(seconds)
