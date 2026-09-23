# generation A ordered scan

class OrderedDict(object):
    def __init__(self, pairs=None):
        self._items = []
        self._index = {}
        if pairs is not None:
            for key, value in pairs:
                if key in self._index:
                    i = self._index[key]
                    self._items[i] = (key, value)
                else:
                    self._index[key] = len(self._items)
                    self._items.append((key, value))

    def __getitem__(self, key):
        if key not in self._index:
            raise KeyError(key)
        i = self._index[key]
        return self._items[i][1]
