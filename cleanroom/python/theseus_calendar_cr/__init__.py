"""Clean-room implementation of calendar utilities.

Implements leap-year arithmetic and weekday computation from scratch
using the proleptic Gregorian calendar.
"""

# Day counts per month for a non-leap year. Index 0 unused.
_DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Day name constants (0=Monday ... 6=Sunday) — matches stdlib convention.
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6


def isleap(year):
    """Return True for a leap year, False otherwise.

    Gregorian rule: divisible by 4, except century years not divisible
    by 400.
    """
    year = int(year)
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def leapdays(y1, y2):
    """Number of leap years in range [y1, y2)."""
    y1 = int(y1)
    y2 = int(y2)
    if y1 > y2:
        y1, y2 = y2, y1
    # Count leap years in [1, n] then subtract.
    a = y1 - 1
    b = y2 - 1
    return ((b // 4) - (a // 4)
            - (b // 100) + (a // 100)
            + (b // 400) - (a // 400))


def weekday(year, month, day):
    """Return weekday (0=Monday ... 6=Sunday) for the given date.

    Uses Zeller's congruence on the proleptic Gregorian calendar.
    """
    y = int(year)
    m = int(month)
    d = int(day)
    if m < 3:
        m += 12
        y -= 1
    # Zeller's congruence: h = 0 -> Saturday, 1 -> Sunday, ..., 6 -> Friday.
    h = (d + (13 * (m + 1)) // 5 + y + y // 4 - y // 100 + y // 400) % 7
    # Convert to 0=Monday convention.
    return (h + 5) % 7


def monthrange(year, month):
    """Return (weekday_of_first, days_in_month) for year/month."""
    year = int(year)
    month = int(month)
    if not 1 <= month <= 12:
        raise ValueError("bad month number %r; must be 1-12" % month)
    days = _DAYS_IN_MONTH[month]
    if month == 2 and isleap(year):
        days = 29
    first_wd = weekday(year, month, 1)
    return (first_wd, days)


def monthlen(year, month):
    """Number of days in the given month."""
    return monthrange(year, month)[1]


# --- Invariant probes ----------------------------------------------------
# These small helpers expose the values referenced in the spec invariants
# so external test harnesses can verify the implementation.

def calendar2_isleap():
    """True — 2024 is a leap year (divisible by 4, not by 100)."""
    return isleap(2024)


def calendar2_monthrange():
    """29 — February 2024 has 29 days."""
    return monthrange(2024, 2)[1]


def calendar2_weekday():
    """0 — January 1, 2024 was a Monday."""
    return weekday(2024, 1, 1)