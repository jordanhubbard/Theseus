"""
theseus_calendar_cr — Clean-room calendar module.
No import of the standard `calendar` module.
"""

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

month_name = ['', 'January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

month_abbr = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
day_abbr = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

_DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def isleap(year):
    """Return True if year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def leapdays(y1, y2):
    """Return count of leap years in range [y1, y2)."""
    y1 -= 1
    y2 -= 1
    return (y2 // 4 - y1 // 4) - (y2 // 100 - y1 // 100) + (y2 // 400 - y1 // 400)


def monthrange(year, month):
    """Return (weekday of first day, number of days) for year/month."""
    if not 1 <= month <= 12:
        raise ValueError(f"bad month number {month}; must be 1-12")
    days = _DAYS_IN_MONTH[month]
    if month == 2 and isleap(year):
        days = 29
    return weekday(year, month, 1), days


def weekday(year, month, day):
    """Return weekday (0=Monday) for year, month, day."""
    # Zeller-like calculation using the Tomohiko Sakamoto algorithm
    if month < 3:
        month += 12
        year -= 1
    k = year % 100
    j = year // 100
    h = (day + (13 * (month + 1)) // 5 + k + k // 4 + j // 4 - 2 * j) % 7
    # h: 0=Sat,1=Sun,2=Mon,...,6=Fri — convert to 0=Mon
    return (h + 5) % 7


def _weeks_in_month(year, month):
    """Return list of weeks; each week is a list of day numbers (0=no day)."""
    first_day, ndays = monthrange(year, month)
    weeks = []
    week = [0] * 7
    day = 1
    col = first_day
    while day <= ndays:
        week[col] = day
        day += 1
        col += 1
        if col == 7:
            weeks.append(week)
            week = [0] * 7
            col = 0
    if col > 0:
        weeks.append(week)
    return weeks


def monthcalendar(year, month):
    """Return matrix of days for given month."""
    return _weeks_in_month(year, month)


def prmonth(theyear, themonth, w=0, l=0):
    """Print single month calendar."""
    print(f'{month_name[themonth]:^{w or 20}} {theyear}')
    print(' '.join(d[:2] for d in day_abbr))
    for week in monthcalendar(theyear, themonth):
        print(' '.join(('%2d' % d if d else '  ') for d in week))


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def calendar2_isleap():
    """isleap(2000) is True, isleap(1900) is False; returns True."""
    return isleap(2000) and not isleap(1900)


def calendar2_monthrange():
    """monthrange(2024, 2) returns days=29 (leap year); returns 29."""
    _, days = monthrange(2024, 2)
    return days


def calendar2_weekday():
    """weekday(2024, 1, 1) returns 0 (Monday); returns 0."""
    return weekday(2024, 1, 1)


__all__ = [
    'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY',
    'month_name', 'month_abbr', 'day_name', 'day_abbr',
    'isleap', 'leapdays', 'monthrange', 'weekday', 'monthcalendar', 'prmonth',
    'calendar2_isleap', 'calendar2_monthrange', 'calendar2_weekday',
]
