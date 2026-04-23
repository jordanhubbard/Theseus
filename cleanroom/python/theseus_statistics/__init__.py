"""
theseus_statistics - Clean-room implementation of basic statistics functions.
"""

import math


def mean(*args, data=None):
    """
    Calculate the arithmetic mean of a list of numbers.

    mean([1, 2, 3, 4, 5]) == 3.0
    mean(1, 2, 3, 4, 5) == 3.0

    Args:
        data: A sequence of numeric values, or pass values as positional args.

    Returns:
        float: The arithmetic mean.

    Raises:
        ValueError: If data is empty.
    """
    if data is not None:
        values = list(data)
    elif len(args) == 1 and hasattr(args[0], '__iter__'):
        values = list(args[0])
    elif len(args) > 0:
        values = list(args)
    else:
        raise ValueError("mean requires at least one data point")
    
    if len(values) == 0:
        raise ValueError("mean requires at least one data point")
    return sum(values) / len(values)


def median(*args, data=None):
    """
    Calculate the median (middle value) of a list of numbers.

    median([1, 2, 3, 4, 5]) == 3

    For an odd number of elements, returns the middle element.
    For an even number of elements, returns the average of the two middle elements.

    Args:
        data: A sequence of numeric values.

    Returns:
        The median value.

    Raises:
        ValueError: If data is empty.
    """
    if data is not None:
        values = sorted(data)
    elif len(args) == 1 and hasattr(args[0], '__iter__'):
        values = sorted(args[0])
    elif len(args) > 0:
        values = sorted(args)
    else:
        raise ValueError("median requires at least one data point")
    
    n = len(values)
    if n == 0:
        raise ValueError("median requires at least one data point")
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    else:
        return (values[mid - 1] + values[mid]) / 2


def stdev(*args, data=None):
    """
    Calculate the sample standard deviation of a list of numbers.

    stdev([2, 4, 4, 4, 5, 5, 7, 9]) == 2.0

    Uses Bessel's correction (divides by N-1) for sample standard deviation.

    Args:
        data: A sequence of numeric values.

    Returns:
        float: The sample standard deviation.

    Raises:
        ValueError: If data has fewer than 2 elements.
    """
    if data is not None:
        values = list(data)
    elif len(args) == 1 and hasattr(args[0], '__iter__'):
        values = list(args[0])
    elif len(args) > 0:
        values = list(args)
    else:
        raise ValueError("stdev requires at least two data points")
    
    n = len(values)
    if n < 2:
        raise ValueError("stdev requires at least two data points")

    m = sum(values) / n
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def stats_mean():
    return mean([1, 2, 3, 4, 5])

def stats_median():
    return median([1, 2, 3, 4, 5])

def pstdev(data):
    values = list(data)
    n = len(values)
    if n < 1:
        raise ValueError("pstdev requires at least one data point")
    m = sum(values) / n
    variance = sum((x - m) ** 2 for x in values) / n
    return variance ** 0.5

def stats_stdev():
    return pstdev([2, 4, 4, 4, 5, 5, 7, 9])