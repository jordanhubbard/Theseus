# generation B walker class


def _index(value):
    try:
        return value.__index__()
    except AttributeError:
        raise TypeError("an integer is required")


class _Walker:
    def __init__(self, kind, pools, size=None):
        self._kind = kind
        self._pools = pools
        self._size = size
        self._started = False
        self._done = False
        if kind == "product":
            self._indices = [0] * len(pools)
            if any(not pool for pool in pools):
                self._done = True
        else:
            count = len(pools[0])
            self._indices = list(range(size))
            if size > count:
                self._done = True

    def __iter__(self):
        return self

    def __next__(self):
        if self._done:
            raise StopIteration
        if not self._started:
            self._started = True
        elif self._kind == "product":
            self._advance_product()
        else:
            self._advance_combinations()
        if self._done:
            raise StopIteration
        if self._kind == "product":
            return tuple(
                pool[index] for pool, index in zip(self._pools, self._indices)
            )
        pool = self._pools[0]
        return tuple(pool[index] for index in self._indices)

    def _advance_product(self):
        for position in range(len(self._indices) - 1, -1, -1):
            next_index = self._indices[position] + 1
            if next_index < len(self._pools[position]):
                self._indices[position] = next_index
                return
            self._indices[position] = 0
        self._done = True

    def _advance_combinations(self):
        count = len(self._pools[0])
        for position in range(self._size - 1, -1, -1):
            if self._indices[position] != position + count - self._size:
                break
        else:
            self._done = True
            return
        self._indices[position] += 1
        for following in range(position + 1, self._size):
            self._indices[following] = self._indices[following - 1] + 1


def product(*iterables, **kwargs):
    unexpected = set(kwargs) - {"repeat"}
    if unexpected:
        name = next(iter(unexpected))
        raise TypeError("product() got an unexpected keyword argument %r" % name)
    repeat = _index(kwargs.get("repeat", 1))
    if repeat < 0:
        raise ValueError("repeat argument cannot be negative")
    pools = [tuple(iterable) for iterable in iterables] * repeat
    return _Walker("product", pools)


def combinations(iterable, r):
    size = _index(r)
    if size < 0:
        raise ValueError("r must be non-negative")
    return _Walker("combinations", [tuple(iterable)], size)
