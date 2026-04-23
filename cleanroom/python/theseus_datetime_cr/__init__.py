"""
theseus_datetime_cr - Clean-room date/time implementation.
No imports of datetime, time, or calendar modules.
"""


def _is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year, month):
    days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and _is_leap_year(year):
        return 29
    return days[month]


def _days_in_year(year):
    return 366 if _is_leap_year(year) else 365


# Compute the number of days from a reference epoch (year 1, Jan 1) to a given date.
def _date_to_ordinal(year, month, day):
    """Convert a (year, month, day) to an ordinal day count (proleptic Gregorian)."""
    # Days in complete years before this year
    y = year - 1
    ordinal = y * 365 + y // 4 - y // 100 + y // 400
    # Days in complete months of this year
    for m in range(1, month):
        ordinal += _days_in_month(year, m)
    ordinal += day
    return ordinal


def _ordinal_to_date(ordinal):
    """Convert an ordinal day count back to (year, month, day)."""
    # Estimate the year
    # Use 400-year cycles: 400 years = 146097 days
    n400, rem = divmod(ordinal - 1, 146097)
    year = n400 * 400 + 1

    # 100-year cycles: 100 years = 36524 days (but first cycle has 36525)
    n100, rem = divmod(rem, 36524)
    if n100 == 4:
        n100 = 3
        rem = 36524
    year += n100 * 100

    # 4-year cycles: 4 years = 1461 days
    n4, rem = divmod(rem, 1461)
    year += n4 * 4

    # Remaining years
    n1, rem = divmod(rem, 365)
    if n1 == 4:
        n1 = 3
        rem = 365
    year += n1

    # Now find month and day
    day_of_year = rem + 1
    month = 1
    while month <= 12:
        dim = _days_in_month(year, month)
        if day_of_year <= dim:
            break
        day_of_year -= dim
        month += 1

    return year, month, day_of_year


class timedelta:
    """Represents a duration."""

    def __init__(self, days=0, seconds=0):
        # Normalize seconds into days
        extra_days, seconds = divmod(seconds, 86400)
        self._days = int(days) + int(extra_days)
        self._seconds = int(seconds)

    @property
    def days(self):
        return self._days

    @property
    def seconds(self):
        return self._seconds

    def __repr__(self):
        return f"timedelta(days={self._days}, seconds={self._seconds})"

    def __eq__(self, other):
        if isinstance(other, timedelta):
            return self._days == other._days and self._seconds == other._seconds
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, timedelta):
            return timedelta(days=self._days + other._days,
                             seconds=self._seconds + other._seconds)
        return NotImplemented

    def __neg__(self):
        return timedelta(days=-self._days, seconds=-self._seconds)

    def __sub__(self, other):
        if isinstance(other, timedelta):
            return self + (-other)
        return NotImplemented


class Date:
    """Immutable date object."""

    def __init__(self, year, month, day):
        if not (1 <= month <= 12):
            raise ValueError(f"Month {month} is out of range 1-12")
        dim = _days_in_month(year, month)
        if not (1 <= day <= dim):
            raise ValueError(f"Day {day} is out of range for month {month}")
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
        """Return date in 'YYYY-MM-DD' format."""
        return f"{self._year:04d}-{self._month:02d}-{self._day:02d}"

    def __repr__(self):
        return f"Date({self._year}, {self._month}, {self._day})"

    def __str__(self):
        return self.isoformat()

    def __eq__(self, other):
        if isinstance(other, Date):
            return (self._year == other._year and
                    self._month == other._month and
                    self._day == other._day)
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, timedelta):
            ordinal = _date_to_ordinal(self._year, self._month, self._day)
            ordinal += other.days
            year, month, day = _ordinal_to_date(ordinal)
            return Date(year, month, day)
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, timedelta):
            return self.__add__(-other)
        if isinstance(other, Date):
            ord1 = _date_to_ordinal(self._year, self._month, self._day)
            ord2 = _date_to_ordinal(other._year, other._month, other._day)
            return timedelta(days=ord1 - ord2)
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Date):
            return (self._year, self._month, self._day) < (other._year, other._month, other._day)
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Date):
            return (self._year, self._month, self._day) <= (other._year, other._month, other._day)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Date):
            return (self._year, self._month, self._day) > (other._year, other._month, other._day)
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Date):
            return (self._year, self._month, self._day) >= (other._year, other._month, other._day)
        return NotImplemented

    def __hash__(self):
        return hash((self._year, self._month, self._day))


# ── Invariant functions ──────────────────────────────────────────────────────

def datetime_date_isoformat():
    """Returns Date(2026, 4, 20).isoformat() == '2026-04-20'"""
    return Date(2026, 4, 20).isoformat()


def datetime_timedelta_days():
    """Returns timedelta(days=5).days == 5"""
    return timedelta(days=5).days


def datetime_date_add():
    """Returns (Date(2026, 4, 20) + timedelta(days=10)).isoformat() == '2026-04-30'"""
    result = Date(2026, 4, 20) + timedelta(days=10)
    return result.isoformat()