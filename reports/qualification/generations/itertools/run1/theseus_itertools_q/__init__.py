# generation A product loops

__all__ = ["product", "combinations"]


def product(*iterables):
    pools = [tuple(it) for it in iterables]
    if not pools:
        yield ()
        return
    for pool in pools:
        if len(pool) == 0:
            return
    n = len(pools)
    indices = [0] * n
    while True:
        yield tuple(pools[i][indices[i]] for i in range(n))
        for i in range(n - 1, -1, -1):
            indices[i] += 1
            if indices[i] < len(pools[i]):
                break
            indices[i] = 0
            if i == 0:
                return


def combinations(iterable, r):
    pool = tuple(iterable)
    n = len(pool)
    if r < 0:
        raise ValueError("r must be non-negative")
    if r == 0:
        yield ()
        return
    if r > n:
        return
    indices = list(range(r))
    while True:
        yield tuple(pool[i] for i in indices)
        for i in range(r - 1, -1, -1):
            if indices[i] != i + n - r:
                break
            indices[i] = i
        else:
            return
        indices[i] += 1
        for j in range(i + 1, r):
            indices[j] = indices[j - 1] + 1
