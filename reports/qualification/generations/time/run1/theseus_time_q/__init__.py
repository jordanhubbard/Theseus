# generation A epoch scan

__all__ = ["gmtime", "GmtimeResult"]


class GmtimeResult:
    __slots__ = (
        "tm_year",
        "tm_mon",
        "tm_mday",
        "tm_hour",
        "tm_min",
        "tm_sec",
    )

    def __init__(self, tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec):
        self.tm_year = tm_year
        self.tm_mon = tm_mon
        self.tm_mday = tm_mday
        self.tm_hour = tm_hour
        self.tm_min = tm_min
        self.tm_sec = tm_sec


def _is_leap(year):
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    return year % 400 == 0


def _days_in_year(year):
    return 366 if _is_leap(year) else 365


def _ymd_from_epoch_day(day):
    year = 1970
    while day >= _days_in_year(year):
        day -= _days_in_year(year)
        year += 1
    while day < 0:
        year -= 1
        day += _days_in_year(year)

    month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if _is_leap(year):
        month_lengths[1] = 29

    month = 1
    for length in month_lengths:
        if day < length:
            break
        day -= length
        month += 1

    return year, month, day + 1


def gmtime(seconds):
    secs = int(seconds)
    day, rem = divmod(secs, 86400)
    if rem < 0:
        rem += 86400
        day -= 1

    tm_hour, rem = divmod(rem, 3600)
    tm_min, tm_sec = divmod(rem, 60)

    tm_year, tm_mon, tm_mday = _ymd_from_epoch_day(day)

    return GmtimeResult(tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec)
