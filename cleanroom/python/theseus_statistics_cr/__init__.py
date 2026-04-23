"""
theseus_statistics_cr — Clean-room statistics module.
No import of the standard `statistics` module.
"""

import math as _math
import operator as _operator


class StatisticsError(ValueError):
    pass


def mean(data):
    """Return arithmetic mean of data."""
    data = list(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("mean requires at least one data point")
    return sum(data) / n


def fmean(data):
    """Return floating-point arithmetic mean of data."""
    data = list(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("fmean requires at least one data point")
    return _math.fsum(data) / n


def geometric_mean(data):
    """Return the geometric mean of data."""
    data = list(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("geometric_mean requires at least one data point")
    return _math.exp(_math.fsum(_math.log(x) for x in data) / n)


def harmonic_mean(data):
    """Return the harmonic mean of data."""
    data = list(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("harmonic_mean requires at least one data point")
    return n / _math.fsum(1 / x for x in data)


def median(data):
    """Return median (middle value) of numeric data."""
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("median requires at least one data point")
    mid = n // 2
    if n % 2 == 0:
        return (data[mid - 1] + data[mid]) / 2
    return data[mid]


def median_low(data):
    """Return low median of numeric data."""
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("median_low requires at least one data point")
    return data[(n - 1) // 2]


def median_high(data):
    """Return high median of numeric data."""
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("median_high requires at least one data point")
    return data[n // 2]


def mode(data):
    """Return most common data point."""
    data = list(data)
    if not data:
        raise StatisticsError("mode requires at least one data point")
    counts = {}
    for x in data:
        counts[x] = counts.get(x, 0) + 1
    return max(counts, key=counts.get)


def multimode(data):
    """Return list of most common values."""
    data = list(data)
    if not data:
        return []
    counts = {}
    for x in data:
        counts[x] = counts.get(x, 0) + 1
    max_count = max(counts.values())
    return [x for x, c in counts.items() if c == max_count]


def variance(data, xbar=None):
    """Return sample variance of data."""
    data = list(data)
    n = len(data)
    if n < 2:
        raise StatisticsError("variance requires at least two data points")
    if xbar is None:
        xbar = mean(data)
    ss = _math.fsum((x - xbar) ** 2 for x in data)
    return ss / (n - 1)


def pvariance(data, mu=None):
    """Return population variance of data."""
    data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError("pvariance requires at least one data point")
    if mu is None:
        mu = mean(data)
    ss = _math.fsum((x - mu) ** 2 for x in data)
    return ss / n


def stdev(data, xbar=None):
    """Return sample standard deviation of data."""
    return _math.sqrt(variance(data, xbar))


def pstdev(data, mu=None):
    """Return population standard deviation of data."""
    return _math.sqrt(pvariance(data, mu))


def quantiles(data, *, n=4, method='exclusive'):
    """Return a list of n-1 cut points dividing data into n equal intervals."""
    data = sorted(data)
    ld = len(data)
    if ld < 2:
        raise StatisticsError("must have at least two data points")
    if n < 1:
        raise StatisticsError("n must be at least 1")
    if method == 'inclusive':
        m = ld - 1
        result = []
        for i in range(1, n):
            j = i * m // n
            delta = i * m - j * n
            interpolated = (data[j] * (n - delta) + data[j + 1] * delta) / n
            result.append(interpolated)
        return result
    else:  # exclusive
        m = ld + 1
        result = []
        for i in range(1, n):
            j = i * ld // n
            delta = i * ld - j * n
            if delta == 0:
                result.append(data[j - 1])
            else:
                result.append(data[j - 1] + (data[j] - data[j - 1]) * delta / n)
        return result


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def statistics2_mean():
    """mean([1,2,3,4,5]) == 3.0; returns 3.0."""
    return mean([1, 2, 3, 4, 5])


def statistics2_median():
    """median([1,3,5]) == 3; returns 3."""
    return median([1, 3, 5])


def statistics2_stdev():
    """stdev([1,2,3,4,5]) approx 1.581; returns True."""
    result = stdev([1, 2, 3, 4, 5])
    return abs(result - 1.5811388300841898) < 0.0001


__all__ = [
    'StatisticsError',
    'mean', 'fmean', 'geometric_mean', 'harmonic_mean',
    'median', 'median_low', 'median_high',
    'mode', 'multimode',
    'variance', 'pvariance', 'stdev', 'pstdev',
    'quantiles',
    'statistics2_mean', 'statistics2_median', 'statistics2_stdev',
]
