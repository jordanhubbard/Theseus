from collections import namedtuple

# struct_time namedtuple with standard fields
struct_time = namedtuple('struct_time', [
    'tm_year', 'tm_mon', 'tm_mday',
    'tm_hour', 'tm_min', 'tm_sec',
    'tm_wday', 'tm_yday', 'tm_isdst'
])

# Days in each month for non-leap and leap years
_DAYS_IN_MONTH = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_DAYS_IN_MONTH_LEAP = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year, month):
    if _is_leap(year):
        return _DAYS_IN_MONTH_LEAP[month]
    return _DAYS_IN_MONTH[month]


def _days_in_year(year):
    return 366 if _is_leap(year) else 365


def gmtime(secs=0):
    """Convert seconds since Unix epoch (1970-01-01 00:00:00 UTC) to struct_time."""
    secs = int(secs)
    
    # Handle negative seconds
    # We need to compute the date/time components
    
    # Separate into days and time-of-day
    # Use floor division to handle negative values correctly
    days = secs // 86400
    remaining = secs % 86400  # Always non-negative due to Python's floor division
    
    tm_hour = remaining // 3600
    remaining = remaining % 3600
    tm_min = remaining // 60
    tm_sec = remaining % 60
    
    # Now compute year, month, day from days since epoch (1970-01-01)
    # day 0 = 1970-01-01
    
    year = 1970
    
    if days >= 0:
        # Forward from epoch
        while True:
            dy = _days_in_year(year)
            if days < dy:
                break
            days -= dy
            year += 1
    else:
        # Backward from epoch
        while days < 0:
            year -= 1
            days += _days_in_year(year)
    
    # days is now the 0-based day of the year
    tm_yday = days + 1  # 1-based
    
    # Find month and day
    month = 1
    while month <= 12:
        dim = _days_in_month(year, month)
        if days < dim:
            break
        days -= dim
        month += 1
    
    tm_mday = days + 1  # 1-based
    tm_mon = month
    tm_year = year
    
    # Compute day of week
    # January 1, 1970 was a Thursday (weekday 3, where Monday=0)
    # We need the absolute day number from epoch
    abs_days = (secs - remaining - (secs % 86400 - remaining)) // 86400
    # Recompute properly
    abs_days = secs // 86400
    # Thursday = 3 (Mon=0), so epoch day 0 is Thursday
    tm_wday = (abs_days + 3) % 7
    if tm_wday < 0:
        tm_wday += 7
    
    return struct_time(
        tm_year=tm_year,
        tm_mon=tm_mon,
        tm_mday=tm_mday,
        tm_hour=tm_hour,
        tm_min=tm_min,
        tm_sec=tm_sec,
        tm_wday=tm_wday,
        tm_yday=tm_yday,
        tm_isdst=-1
    )


def mktime(t):
    """Convert struct_time to seconds since Unix epoch (inverse of gmtime)."""
    year = t.tm_year
    month = t.tm_mon
    mday = t.tm_mday
    hour = t.tm_hour
    minute = t.tm_min
    sec = t.tm_sec
    
    # Count days from 1970-01-01 to the given date
    # First, count days from 1970 to the start of the given year
    days = 0
    
    if year >= 1970:
        for y in range(1970, year):
            days += _days_in_year(y)
    else:
        for y in range(year, 1970):
            days -= _days_in_year(y)
    
    # Add days for months in the given year
    for m in range(1, month):
        days += _days_in_month(year, m)
    
    # Add days for the day of month (1-based, so subtract 1)
    days += mday - 1
    
    # Convert to seconds
    total = days * 86400 + hour * 3600 + minute * 60 + sec
    
    return float(total)


# Test functions as specified in invariants
def time_gmtime_epoch():
    return gmtime(0).tm_year


def time_gmtime_month():
    return gmtime(0).tm_mon


def time_mktime_roundtrip():
    return mktime(gmtime(86400))