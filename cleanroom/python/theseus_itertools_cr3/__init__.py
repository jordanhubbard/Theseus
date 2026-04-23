def tee(iterable, n=2):
    """Return n independent iterators from a single iterable."""
    iterator = iter(iterable)
    # Each clone has its own list used as a queue of pending items
    queues = [[] for _ in range(n)]
    
    def gen(my_queue):
        while True:
            if not my_queue:
                # Need to fetch next item from the shared iterator
                try:
                    val = next(iterator)
                except StopIteration:
                    return
                # Distribute to all queues
                for q in queues:
                    q.append(val)
            yield my_queue.pop(0)
    
    return tuple(gen(q) for q in queues)


def pairwise(iterable):
    """Yield consecutive overlapping pairs."""
    iterator = iter(iterable)
    try:
        prev = next(iterator)
    except StopIteration:
        return
    for current in iterator:
        yield (prev, current)
        prev = current


def batched(iterable, n):
    """Yield tuples of length n; last tuple may be shorter."""
    if n < 1:
        raise ValueError("n must be at least one")
    iterator = iter(iterable)
    while True:
        batch = []
        try:
            for _ in range(n):
                batch.append(next(iterator))
        except StopIteration:
            if batch:
                yield tuple(batch)
            return
        yield tuple(batch)


def itertools3_tee():
    a, b = tee([1, 2, 3])
    return list(a) == [1, 2, 3] and list(b) == [1, 2, 3]


def itertools3_pairwise():
    return len(list(pairwise([1, 2, 3, 4])))


def itertools3_batched():
    return len(list(batched([1, 2, 3, 4, 5], 2)))