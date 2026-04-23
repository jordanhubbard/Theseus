"""
theseus_datetime_cr2 - Clean-room implementation of datetime utilities.
Provides timedelta and timezone classes without importing the datetime module.
"""


class timedelta:
    """
    Represents a duration: days, seconds, microseconds.
    Normalizes so that:
      0 <= microseconds < 1_000_000
      0 <= seconds < 86400
      days can be any integer (positive, negative, or zero)
    """

    __slots__ = ('_days', '_seconds', '_microseconds')

    def __init__(self, days=0, seconds=0, microseconds=0,
                 milliseconds=0, minutes=0, hours=0, weeks=0):
        # Convert everything to microseconds first, then normalize
        total_microseconds = int(microseconds)
        total_microseconds += int(milliseconds) * 1_000
        total_microseconds += int(seconds) * 1_000_000
        total_microseconds += int(minutes) * 60 * 1_000_000
        total_microseconds += int(hours) * 3600 * 1_000_000
        total_microseconds += int(days) * 86400 * 1_000_000
        total_microseconds += int(weeks) * 7 * 86400 * 1_000_000

        # Normalize
        us = total_microseconds % 1_000_000
        total_seconds = (total_microseconds - us) // 1_000_000
        s = total_seconds % 86400
        d = (total_seconds - s) // 86400

        object.__setattr__(self, '_days', d)
        object.__setattr__(self, '_seconds', s)
        object.__setattr__(self, '_microseconds', us)

    def __setattr__(self, name, value):
        raise AttributeError("timedelta objects are immutable")

    @property
    def days(self):
        return self._days

    @property
    def seconds(self):
        return self._seconds

    @property
    def microseconds(self):
        return self._microseconds

    def total_seconds(self):
        """Return total duration in seconds as a float."""
        return (self._days * 86400 +
                self._seconds +
                self._microseconds / 1_000_000)

    def __add__(self, other):
        if isinstance(other, timedelta):
            return timedelta(
                days=self._days + other._days,
                seconds=self._seconds + other._seconds,
                microseconds=self._microseconds + other._microseconds
            )
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, timedelta):
            return timedelta(
                days=self._days - other._days,
                seconds=self._seconds - other._seconds,
                microseconds=self._microseconds - other._microseconds
            )
        return NotImplemented

    def __neg__(self):
        return timedelta(
            days=-self._days,
            seconds=-self._seconds,
            microseconds=-self._microseconds
        )

    def __pos__(self):
        return timedelta(
            days=self._days,
            seconds=self._seconds,
            microseconds=self._microseconds
        )

    def __abs__(self):
        if self._days < 0:
            return -self
        return self

    def __mul__(self, other):
        if isinstance(other, int):
            return timedelta(
                days=self._days * other,
                seconds=self._seconds * other,
                microseconds=self._microseconds * other
            )
        if isinstance(other, float):
            total_us = (self._days * 86400 * 1_000_000 +
                        self._seconds * 1_000_000 +
                        self._microseconds)
            result_us = round(total_us * other)
            return timedelta(microseconds=result_us)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __eq__(self, other):
        if isinstance(other, timedelta):
            return (self._days == other._days and
                    self._seconds == other._seconds and
                    self._microseconds == other._microseconds)
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, timedelta):
            return self.total_seconds() < other.total_seconds()
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, timedelta):
            return self.total_seconds() <= other.total_seconds()
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, timedelta):
            return self.total_seconds() > other.total_seconds()
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, timedelta):
            return self.total_seconds() >= other.total_seconds()
        return NotImplemented

    def __bool__(self):
        return (self._days != 0 or
                self._seconds != 0 or
                self._microseconds != 0)

    def __hash__(self):
        return hash((self._days, self._seconds, self._microseconds))

    def __repr__(self):
        args = []
        if self._days:
            args.append(f'days={self._days}')
        if self._seconds:
            args.append(f'seconds={self._seconds}')
        if self._microseconds:
            args.append(f'microseconds={self._microseconds}')
        if not args:
            args.append('0')
        return f'timedelta({", ".join(args)})'

    def __str__(self):
        total = int(self.total_seconds())
        if self._days < 0:
            sign = '-'
            total = -total
        else:
            sign = ''
        hours, rem = divmod(total, 3600)
        minutes, seconds = divmod(rem, 60)
        if self._microseconds:
            return f'{sign}{hours}:{minutes:02d}:{seconds:02d}.{abs(self._microseconds):06d}'
        return f'{sign}{hours}:{minutes:02d}:{seconds:02d}'


class timezone:
    """
    Fixed-offset timezone.
    """

    def __init__(self, offset, name=None):
        if not isinstance(offset, timedelta):
            raise TypeError("offset must be a timedelta")
        # Validate offset range: must be strictly between -24h and +24h
        limit = timedelta(hours=24)
        if not (-limit < offset < limit):
            raise ValueError("offset must be a timedelta strictly between "
                             "-timedelta(hours=24) and timedelta(hours=24).")
        self._offset = offset
        self._name = name

    def utcoffset(self, dt):
        """Return the UTC offset for this timezone."""
        return self._offset

    def tzname(self, dt):
        """Return the timezone name."""
        if self._name is not None:
            return self._name
        total_seconds = int(self._offset.total_seconds())
        if total_seconds == 0:
            return 'UTC'
        sign = '+' if total_seconds >= 0 else '-'
        total_seconds = abs(total_seconds)
        hours, rem = divmod(total_seconds, 3600)
        minutes = rem // 60
        if minutes:
            return f'UTC{sign}{hours:02d}:{minutes:02d}'
        return f'UTC{sign}{hours:02d}:00'

    def dst(self, dt):
        """Return None (fixed offset, no DST)."""
        return timedelta(0)

    def fromutc(self, dt):
        raise NotImplementedError("fromutc not implemented")

    def __eq__(self, other):
        if isinstance(other, timezone):
            return self._offset == other._offset
        return NotImplemented

    def __hash__(self):
        return hash(self._offset)

    def __repr__(self):
        if self._offset == timedelta(0):
            return 'datetime.timezone.utc'
        if self._name is not None:
            return f'datetime.timezone({self._offset!r}, {self._name!r})'
        return f'datetime.timezone({self._offset!r})'

    def __str__(self):
        return self.tzname(None)


# Create the UTC singleton
timezone.utc = timezone(timedelta(0), 'UTC')


# ── Required exported functions ──────────────────────────────────────────────

def datetime2_timedelta_seconds():
    """timedelta(days=1).total_seconds() == 86400.0"""
    return timedelta(days=1).total_seconds()


def datetime2_timedelta_add():
    """(timedelta(days=1) + timedelta(hours=12)).total_seconds() == 129600.0"""
    return (timedelta(days=1) + timedelta(hours=12)).total_seconds()


def datetime2_timezone_utc():
    """timezone.utc.utcoffset(None).total_seconds() == 0.0"""
    return timezone.utc.utcoffset(None).total_seconds()