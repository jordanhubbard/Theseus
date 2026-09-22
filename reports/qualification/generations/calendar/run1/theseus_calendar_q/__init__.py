# generation A date arithmetic

_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def isleap(year):
    """Return True for leap years, False otherwise."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def weekday(year, month, day):
    """Return weekday (0=Monday .. 6=Sunday) for the given proleptic Gregorian date."""
    if month < 3:
        month += 12
        year -= 1
    century = year // 100
    year_in_century = year % 100
    h = (
        day
        + (13 * (month + 1) // 5)
        + year_in_century
        + year_in_century // 4
        + century // 4
        - 2 * century
    ) % 7
    return (h + 5) % 7


def leapdays(y1, y2):
    """Return the number of leap years in the half-open range [y1, y2)."""
    if y1 > y2:
        return -leapdays(y2, y1)
    y1 -= 1
    return (
        (y2 // 4 - y1 // 4)
        - (y2 // 100 - y1 // 100)
        + (y2 // 400 - y1 // 400)
    )


def monthrange(year, month):
    """Return (weekday of the first day, number of days in month)."""
    if month == 2 and isleap(year):
        num_days = 29
    else:
        num_days = _DAYS_IN_MONTH[month - 1]
    return weekday(year, month, 1), num_days
