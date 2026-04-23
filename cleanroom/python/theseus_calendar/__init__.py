"""
theseus_calendar - Clean-room calendar utilities.
No import of the standard `calendar` module.
"""


def isleap(year: int) -> bool:
    """Return True if year is a leap year, False otherwise."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year: int, month: int) -> int:
    """Return the number of days in the given month of the given year."""
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    elif month in (4, 6, 9, 11):
        return 30
    elif month == 2:
        return 29 if isleap(year) else 28
    else:
        raise ValueError(f"Invalid month: {month}")


def weekday(year: int, month: int, day: int) -> int:
    """
    Return the day of the week for the given date.
    0 = Monday, 6 = Sunday.
    """
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    y = year
    if month < 3:
        y -= 1
    # Gives 0=Sunday, 1=Monday, ..., 6=Saturday
    dow_sunday_based = (y + y // 4 - y // 100 + y // 400 + t[month - 1] + day) % 7
    # Convert to 0=Monday, 6=Sunday
    return (dow_sunday_based + 6) % 7


def monthrange(year: int, month: int) -> list:
    """
    Return a list [weekday_of_first_day, number_of_days_in_month].
    weekday_of_first_day: 0=Monday, 6=Sunday.
    """
    first_day_weekday = weekday(year, month, 1)
    days = _days_in_month(year, month)
    return [first_day_weekday, days]


# Named convenience functions for specific test cases

def calendar_isleap_2000() -> bool:
    """Return whether year 2000 is a leap year."""
    return isleap(2000)


def calendar_isleap_1900() -> bool:
    """Return whether year 1900 is a leap year."""
    return isleap(1900)


def calendar_monthrange_jan2026() -> list:
    """Return monthrange for January 2026."""
    return monthrange(2026, 1)