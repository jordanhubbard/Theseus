# generation A span scan

_US_PER_SECOND = 1000000
_SECONDS_PER_DAY = 86400
_US_PER_DAY = _SECONDS_PER_DAY * _US_PER_SECOND


class _Scan(object):
    __slots__ = ("days", "seconds", "microseconds")

    def __init__(self, days, seconds, microseconds):
        self.days = days
        self.seconds = seconds
        self.microseconds = microseconds


def _fold(days, seconds, microseconds, milliseconds, minutes, hours, weeks):
    return _Scan(
        int(days) + int(weeks) * 7,
        int(seconds) + int(minutes) * 60 + int(hours) * 3600,
        int(microseconds) + int(milliseconds) * 1000,
    )


def _normalize(scan):
    total = (
        scan.days * _US_PER_DAY
        + scan.seconds * _US_PER_SECOND
        + scan.microseconds
    )
    days, rest = divmod(total, _US_PER_DAY)
    if rest < 0:
        days -= 1
        rest += _US_PER_DAY
    seconds, microseconds = divmod(rest, _US_PER_SECOND)
    if microseconds < 0:
        seconds -= 1
        microseconds += _US_PER_SECOND
    return _Scan(days, seconds, microseconds)


class timedelta(object):
    __slots__ = ("days", "seconds", "microseconds")

    def __init__(
        self,
        days=0,
        seconds=0,
        microseconds=0,
        milliseconds=0,
        minutes=0,
        hours=0,
        weeks=0,
    ):
        scan = _normalize(
            _fold(
                days,
                seconds,
                microseconds,
                milliseconds,
                minutes,
                hours,
                weeks,
            )
        )
        self.days = scan.days
        self.seconds = scan.seconds
        self.microseconds = scan.microseconds
