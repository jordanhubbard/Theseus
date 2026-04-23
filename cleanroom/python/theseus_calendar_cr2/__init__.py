"""
theseus_calendar_cr2 - Clean-room calendar utilities.
Do NOT import the standard `calendar` module.
"""

# Month names: index 0 is empty string, indices 1-12 are full English month names
month_name = [
    '',
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

# Month abbreviations: index 0 is empty string, indices 1-12 are 3-letter abbreviations
month_abbr = [
    '',
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

# Days in each month for non-leap years (index 0 unused)
_DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def isleap(year):
    """Return True if year is a leap year, False otherwise.
    
    Leap year rules:
    - Divisible by 4
    - Except century years (divisible by 100) unless also divisible by 400
    """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year, month):
    """Return the number of days in the given month of the given year."""
    if month == 2 and isleap(year):
        return 29
    return _DAYS_IN_MONTH[month]


def weekday(year, month, day):
    """Return the day of the week for the given date.
    
    Monday is 0, Sunday is 6.
    Uses Tomohiko Sakamoto's algorithm (variant of Zeller's).
    """
    # Using Sakamoto's algorithm
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if month < 3:
        year -= 1
    # Result is 0=Sunday, 1=Monday, ..., 6=Saturday
    dow_sunday_based = (year + year // 4 - year // 100 + year // 400 + t[month - 1] + day) % 7
    # Convert to Monday=0 system: Sunday(0) -> 6, Monday(1) -> 0, ..., Saturday(6) -> 5
    return (dow_sunday_based + 6) % 7


def monthrange(year, month):
    """Return (weekday of first day of month, number of days in month).
    
    Weekday is Monday=0, Sunday=6.
    """
    first_day_weekday = weekday(year, month, 1)
    num_days = _days_in_month(year, month)
    return (first_day_weekday, num_days)


# Zero-arg invariant functions for testing

def calendar2_monthrange():
    """Return monthrange(2024, 2) == (3, 29)"""
    result = monthrange(2024, 2)
    return list(result)


def calendar2_isleap():
    """Return isleap(2024) == True"""
    return isleap(2024)


def calendar2_month_name():
    """Return month_name[1] == 'January'"""
    return month_name[1]