# generation A mean loops

class StatisticsError(ValueError):
    pass


def fmean(data):
    total = 0.0
    count = 0
    for x in data:
        total += float(x)
        count += 1
    if count == 0:
        raise StatisticsError("fmean requires at least one data point")
    return total / count


def median(data):
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    mid = n // 2
    if n % 2:
        return data[mid]
    lo = data[mid - 1]
    hi = data[mid]
    return (lo + hi) / 2
