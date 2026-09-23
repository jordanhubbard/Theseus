# generation B bag factory


class _Bag:
    def __init__(self, iterable):
        self._counts = {}
        for item in iterable:
            self._counts[item] = self._counts.get(item, 0) + 1

    def most_common(self, n=None):
        items = sorted(
            self._counts.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if n is None:
            return items
        return items[:max(0, n)]


def Counter(iterable):
    return _Bag(iterable)
