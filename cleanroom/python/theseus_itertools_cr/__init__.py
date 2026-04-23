"""
theseus_itertools_cr - Clean-room implementation of itertools functions.
No import of itertools or any third-party library.
"""


def chain(*iterables):
    """Chain multiple iterables together into a single iterator."""
    for iterable in iterables:
        for item in iterable:
            yield item


def islice(iterable, *args):
    """
    islice(iterable, stop)
    islice(iterable, start, stop[, step])
    
    Return an iterator whose next() method returns selected values from an iterable.
    """
    # Parse arguments similar to slice()
    if len(args) == 1:
        start = 0
        stop = args[0]
        step = 1
    elif len(args) == 2:
        start = args[0]
        stop = args[1]
        step = 1
    elif len(args) == 3:
        start = args[0]
        stop = args[1]
        step = args[2]
    else:
        raise TypeError(f"islice expected at most 4 arguments, got {1 + len(args)}")

    if start is None:
        start = 0
    if step is None:
        step = 1

    if start < 0 or (stop is not None and stop < 0) or step <= 0:
        raise ValueError("Indices for islice() must be None or an integer: 0 <= x <= sys.maxsize.")

    it = iter(iterable)
    current = 0

    # Skip elements before start
    while current < start:
        try:
            next(it)
            current += 1
        except StopIteration:
            return

    if stop is None:
        # Yield everything from start with given step
        index = start
        while True:
            try:
                value = next(it)
                yield value
                # Skip step-1 elements
                for _ in range(step - 1):
                    next(it)
                index += step
            except StopIteration:
                return
    else:
        index = start
        while index < stop:
            try:
                value = next(it)
                yield value
                index += step
                # Skip step-1 elements
                for _ in range(step - 1):
                    try:
                        next(it)
                    except StopIteration:
                        return
            except StopIteration:
                return


def product(*iterables, repeat=1):
    """
    Cartesian product of input iterables.
    Equivalent to nested for-loops.
    """
    # Convert all iterables to lists (and apply repeat)
    pools = [list(pool) for pool in iterables] * repeat
    
    result = [()]
    for pool in pools:
        result = [x + (y,) for x in result for y in pool]
    
    for item in result:
        yield item


def combinations(iterable, r):
    """
    Return r-length subsequences of elements from the input iterable.
    Combinations are emitted in lexicographic order.
    """
    pool = list(iterable)
    n = len(pool)
    
    if r > n:
        return
    
    # Generate indices
    indices = list(range(r))
    yield tuple(pool[i] for i in indices)
    
    while True:
        # Find the rightmost index that can be incremented
        for i in range(r - 1, -1, -1):
            if indices[i] != i + n - r:
                break
        else:
            return
        
        indices[i] += 1
        for j in range(i + 1, r):
            indices[j] = indices[j - 1] + 1
        
        yield tuple(pool[i] for i in indices)


def permutations(iterable, r=None):
    """
    Return successive r-length permutations of elements in the iterable.
    If r is not specified or is None, then r defaults to the length of the iterable.
    """
    pool = list(iterable)
    n = len(pool)
    
    if r is None:
        r = n
    
    if r > n:
        return
    
    indices = list(range(n))
    cycles = list(range(n, n - r, -1))
    
    yield tuple(pool[i] for i in indices[:r])
    
    while n:
        for i in range(r - 1, -1, -1):
            cycles[i] -= 1
            if cycles[i] == 0:
                # Move the element at position i to the end
                indices[i:] = indices[i + 1:] + indices[i:i + 1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                yield tuple(pool[k] for k in indices[:r])
                break
        else:
            return


def accumulate(iterable, func=None, *, initial=None):
    """
    Return running totals (or other accumulated results).
    """
    it = iter(iterable)
    
    if initial is not None:
        total = initial
        yield total
    else:
        try:
            total = next(it)
        except StopIteration:
            return
        yield total
    
    for element in it:
        if func is None:
            total = total + element
        else:
            total = func(total, element)
        yield total


def cycle(iterable):
    """
    Return elements from the iterable until it is exhausted.
    Then repeat the sequence indefinitely.
    """
    saved = []
    for element in iterable:
        yield element
        saved.append(element)
    
    if not saved:
        return
    
    while True:
        for element in saved:
            yield element


def repeat(object, times=None):
    """
    Return object over and over again. Runs indefinitely unless the times argument is specified.
    """
    if times is None:
        while True:
            yield object
    else:
        for _ in range(times):
            yield object


# Test functions referenced in invariants
def itertools_chain():
    return list(chain([1, 2], [3, 4]))


def itertools_islice():
    return list(islice(range(10), 3))


def itertools_combinations():
    return [list(c) for c in combinations([1, 2, 3], 2)]