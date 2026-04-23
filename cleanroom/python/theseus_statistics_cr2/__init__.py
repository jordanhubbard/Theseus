"""
theseus_statistics_cr2 - Clean-room extended statistics implementation.
"""


def median(data):
    """
    Compute the median (middle value) of the data.
    For even-length data, returns the average of the two middle values.
    """
    if not data:
        raise ValueError("median() requires at least one data point")
    
    sorted_data = sorted(data)
    n = len(sorted_data)
    mid = n // 2
    
    if n % 2 == 1:
        return sorted_data[mid]
    else:
        return (sorted_data[mid - 1] + sorted_data[mid]) / 2.0


def mode(data):
    """
    Compute the mode (most common value) of the data.
    If there is a tie, return the smallest value.
    """
    if not data:
        raise ValueError("mode() requires at least one data point")
    
    counts = {}
    for value in data:
        counts[value] = counts.get(value, 0) + 1
    
    max_count = max(counts.values())
    
    # Get all values with the maximum count, then return the smallest
    candidates = [v for v, c in counts.items() if c == max_count]
    return min(candidates)


def variance(data):
    """
    Compute the sample variance with Bessel's correction (divide by n-1).
    """
    if len(data) < 2:
        raise ValueError("variance() requires at least two data points")
    
    n = len(data)
    mean = sum(data) / n
    
    sum_sq_diff = sum((x - mean) ** 2 for x in data)
    
    return sum_sq_diff / (n - 1)


def statistics2_median():
    """
    Returns median([1, 2, 3, 4, 5]) == 3
    """
    return median([1, 2, 3, 4, 5])


def statistics2_mode():
    """
    Returns mode([1, 2, 2, 3]) == 2
    """
    return mode([1, 2, 2, 3])


def statistics2_variance():
    """
    Returns True if variance([2,4,4,4,5,5,7,9]) is approximately 4.571...
    """
    result = variance([2, 4, 4, 4, 5, 5, 7, 9])
    expected = 32.0 / 7.0  # approximately 4.571428...
    return abs(result - expected) < 1e-9