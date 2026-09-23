# generation B span class


class _Span:
    __slots__ = ("_days", "_seconds", "_microseconds")

    _MICROSECONDS_PER_SECOND = 1000000
    _SECONDS_PER_DAY = 86400
    _MICROSECONDS_PER_DAY = _SECONDS_PER_DAY * _MICROSECONDS_PER_SECOND

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
        total_seconds = (
            days * self._SECONDS_PER_DAY
            + seconds
            + minutes * 60
            + hours * 3600
            + weeks * 7 * self._SECONDS_PER_DAY
        )
        total_microseconds = round(
            total_seconds * self._MICROSECONDS_PER_SECOND
            + milliseconds * 1000
            + microseconds
        )

        normalized_days, remainder = divmod(
            total_microseconds, self._MICROSECONDS_PER_DAY
        )
        normalized_seconds, normalized_microseconds = divmod(
            remainder, self._MICROSECONDS_PER_SECOND
        )

        self._days = normalized_days
        self._seconds = normalized_seconds
        self._microseconds = normalized_microseconds

    @property
    def days(self):
        return self._days

    @property
    def seconds(self):
        return self._seconds

    @property
    def microseconds(self):
        return self._microseconds


timedelta = _Span
