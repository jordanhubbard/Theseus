# generation A mode scan

from collections import Counter


class StatisticsError(ValueError):
    pass


def mode(data):
    try:
        iterator = iter(data)
    except TypeError:
        raise
    counts = Counter(iterator)
    if not counts:
        raise StatisticsError("no mode for empty data")
    max_count = max(counts.values())
    candidates = [key for key, count in counts.items() if count == max_count]
    if len(candidates) > 1:
        raise StatisticsError("no unique mode; found %r" % candidates)
    return candidates[0]
