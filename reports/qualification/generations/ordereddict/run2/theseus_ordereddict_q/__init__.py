# generation B ordered class


class _Ordered:
    def __init__(self, pairs):
        self._keys = []
        self._values = {}
        for key, value in pairs:
            if key not in self._values:
                self._keys.append(key)
            self._values[key] = value

    def __getitem__(self, key):
        return self._values[key]


OrderedDict = _Ordered
