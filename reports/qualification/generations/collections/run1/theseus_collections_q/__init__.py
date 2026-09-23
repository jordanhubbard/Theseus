# generation A counter dict


class Counter(dict):

    def __init__(self, iterable=None, **kwds):
        dict.__init__(self)
        self._first_seen = []
        self._seen = set()
        if iterable is not None:
            self._accumulate_from_iterable(iterable)
        if kwds:
            self._accumulate_from_mapping(kwds)

    def __missing__(self, key):
        return 0

    def _register(self, key):
        if key not in self._seen:
            self._seen.add(key)
            self._first_seen.append(key)

    def _accumulate_from_mapping(self, mapping):
        for key, value in mapping.items():
            self._register(key)
            self[key] = self[key] + value

    def _accumulate_from_iterable(self, iterable):
        if isinstance(iterable, dict):
            self._accumulate_from_mapping(iterable)
            return
        if hasattr(iterable, "items"):
            items = getattr(iterable, "items", None)
            if callable(items) and not isinstance(iterable, (str, bytes, bytearray)):
                self._accumulate_from_mapping(iterable)
                return
        for element in iterable:
            self._register(element)
            self[element] = self[element] + 1

    def most_common(self, n=None):
        ordered = sorted(
            self.items(),
            key=lambda item: (-item[1], self._first_seen.index(item[0])),
        )
        if n is None:
            return ordered
        return ordered[:n]
