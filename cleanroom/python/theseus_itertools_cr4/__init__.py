"""
theseus_itertools_cr4 - Clean-room implementation of extended itertools utilities.
No import of itertools allowed.
"""

import operator as _operator


def islice(iterable, *args):
    """
    islice(iterable, stop) -> iterator
    islice(iterable, start, stop[, step]) -> iterator
    
    Return an iterator whose next() method returns selected values from an
    iterable. If start is specified, will skip all preceding elements;
    otherwise, start defaults to zero. Step defaults to one. If
    specified as another value, step determines how many values are 
    skipped between successive calls. Works like a slice() on a list
    but returns an iterator.
    """
    # Parse arguments
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
    
    if start < 0:
        raise ValueError("Indices for islice() must be None or an integer: 0 <= x <= sys.maxsize.")
    if stop is not None and stop < 0:
        raise ValueError("Indices for islice() must be None or an integer: 0 <= x <= sys.maxsize.")
    if step <= 0:
        raise ValueError("Step for islice() must be a positive integer or None.")
    
    it = iter(iterable)
    
    # Skip 'start' elements
    current = 0
    while current < start:
        try:
            next(it)
            current += 1
        except StopIteration:
            return
    
    # Now yield elements up to stop, stepping by step
    count = start
    while stop is None or count < stop:
        try:
            value = next(it)
        except StopIteration:
            return
        yield value
        count += 1
        # Skip (step - 1) elements
        for _ in range(step - 1):
            try:
                next(it)
                count += 1
            except StopIteration:
                return
            if stop is not None and count >= stop:
                return


def starmap(function, iterable):
    """
    starmap(function, iterable) -> iterator
    
    Return an iterator whose values are returned from the function evaluated
    with an argument tuple taken from the given sequence.
    """
    for args in iterable:
        yield function(*args)


def accumulate(iterable, func=None, *, initial=None):
    """
    accumulate(iterable[, func, *, initial=None]) -> iterator
    
    Return series of accumulated sums (or other binary function results).
    If initial is provided, the accumulation leads off with this value and
    will be one element longer than the input iterable.
    """
    if func is None:
        func = _operator.add
    
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
        total = func(total, element)
        yield total


def chain(*iterables):
    """
    chain(*iterables) -> iterator
    
    Return a chain object whose .__next__() method returns elements from the
    first iterable until it is exhausted, then elements from the next
    iterable, until all of the iterables are exhausted.
    """
    for iterable in iterables:
        for element in iterable:
            yield element


def product(*iterables, repeat=1):
    """
    product(*iterables, repeat=1) -> iterator
    
    Cartesian product of input iterables. Equivalent to nested for-loops.
    """
    # Convert all iterables to lists (and repeat them)
    pools = [list(pool) for pool in iterables] * repeat
    
    result = [[]]
    for pool in pools:
        result = [x + [y] for x in result for y in pool]
    
    for prod in result:
        yield tuple(prod)


def permutations(iterable, r=None):
    """
    permutations(iterable[, r]) -> iterator
    
    Return successive r-length permutations of elements in the iterable.
    If r is not specified or is None, then r defaults to the length of
    the iterable and all possible full-length permutations are generated.
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
                indices[i:] = indices[i + 1:] + indices[i:i + 1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                yield tuple(pool[i] for i in indices[:r])
                break
        else:
            return


def combinations(iterable, r):
    """
    combinations(iterable, r) -> iterator
    
    Return successive r-length combinations of elements in the iterable.
    The combination tuples are emitted in lexicographic ordering according
    to the order of the input iterable. So, if the input iterable is sorted,
    the combination tuples will be produced in sorted order.
    """
    pool = list(iterable)
    n = len(pool)
    
    if r > n:
        return
    
    indices = list(range(r))
    yield tuple(pool[i] for i in indices)
    
    while True:
        for i in range(r - 1, -1, -1):
            if indices[i] != i + n - r:
                break
        else:
            return
        
        indices[i] += 1
        for j in range(i + 1, r):
            indices[j] = indices[j - 1] + 1
        
        yield tuple(pool[i] for i in indices)


# Zero-arg invariant functions

def itertools4_islice():
    """Return list(islice(range(10), 3)) == [0, 1, 2]"""
    return list(islice(range(10), 3))


def itertools4_starmap():
    """Return list(starmap(pow, [(2,2),(3,2)])) == [4, 9]"""
    return list(starmap(pow, [(2, 2), (3, 2)]))


def itertools4_accumulate():
    """Return list(accumulate([1,2,3,4])) == [1, 3, 6, 10]"""
    return list(accumulate([1, 2, 3, 4]))