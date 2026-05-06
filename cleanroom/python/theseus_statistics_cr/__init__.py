"""Clean-room implementation of a statistics module.

Implements arithmetic mean, median, sample variance, sample standard
deviation, and mode without importing the original ``statistics`` module.
"""

import math


class StatisticsError(ValueError):
    """Raised when a statistics computation cannot be performed."""


def _to_list(data):
    """Materialize an iterable into a list of numeric values."""
    if data is None:
        raise StatisticsError("data must not be None")
    values = list(data)
    if len(values) == 0:
        raise StatisticsError("data must contain at least one value")
    return values


def mean(data):
    """Return the arithmetic mean of ``data``."""
    values = _to_list(data)
    total = 0.0
    count = 0
    for v in values:
        total += v
        count += 1
    return total / count


def median(data):
    """Return the median (middle value) of ``data``.

    For an even-length sample, returns the average of the two middle values.
    """
    values = sorted(_to_list(data))
    n = len(values)
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def variance(data):
    """Return the sample variance of ``data`` (Bessel-corrected, n-1 denom)."""
    values = _to_list(data)
    n = len(values)
    if n < 2:
        raise StatisticsError("variance requires at least two data points")
    m = mean(values)
    total = 0.0
    for v in values:
        diff = v - m
        total += diff * diff
    return total / (n - 1)


def stdev(data):
    """Return the sample standard deviation of ``data``."""
    return math.sqrt(variance(data))


def mode(data):
    """Return the most common value in ``data``.

    If multiple values tie for the highest frequency, the one encountered
    first in the input is returned. Raises ``StatisticsError`` if the input
    is empty.
    """
    values = _to_list(data)
    counts = {}
    order = []
    for v in values:
        # Use a key that distinguishes equal-but-different-typed values
        # while keeping hashable values workable.
        try:
            if v not in counts:
                counts[v] = 0
                order.append(v)
            counts[v] += 1
        except TypeError:
            # Fallback for unhashable items: linear scan via order list
            found = False
            for i, existing in enumerate(order):
                if existing == v:
                    counts[i] = counts.get(i, 0) + 1
                    found = True
                    break
            if not found:
                order.append(v)
                counts[len(order) - 1] = 1

    best = None
    best_count = -1
    for item in order:
        c = counts[item] if not isinstance(item, int) or item in counts else counts.get(item, 0)
        # Look up by value when keyed by value, by index when keyed by index
        if item in counts:
            c = counts[item]
        else:
            c = counts[order.index(item)]
        if c > best_count:
            best_count = c
            best = item
    return best


# ---------------------------------------------------------------------------
# Invariant probes — used by the verification harness.
# ---------------------------------------------------------------------------

def statistics2_mean():
    """Mean of [1, 2, 3, 4, 5] is 3.0."""
    return mean([1, 2, 3, 4, 5])


def statistics2_median():
    """Median of [1, 2, 3, 4, 5] is 3."""
    return median([1, 2, 3, 4, 5])


def statistics2_stdev():
    """Sample stdev of [1,2,3,4,5] equals sqrt(2.5)."""
    expected = math.sqrt(2.5)
    actual = stdev([1, 2, 3, 4, 5])
    return abs(actual - expected) < 1e-9