"""
theseus_itertools_cr2 - Clean-room extended itertools (no import of itertools)
"""


def groupby(iterable, key=None):
    """
    Group consecutive elements with the same key.
    Yields (key_value, group_iterator) pairs.
    """
    if key is None:
        key = lambda x: x

    sentinel = object()
    current_key = sentinel
    current_group = []

    for item in iterable:
        k = key(item)
        if current_key is sentinel:
            current_key = k
            current_group.append(item)
        elif k == current_key:
            current_group.append(item)
        else:
            yield current_key, iter(current_group)
            current_key = k
            current_group = [item]

    if current_group:
        yield current_key, iter(current_group)


def zip_longest(*iterables, fillvalue=None):
    """
    Zip iterables, filling shorter ones with fillvalue.
    """
    iterators = [iter(it) for it in iterables]
    if not iterators:
        return

    sentinel = object()
    while True:
        values = []
        all_exhausted = True
        for it in iterators:
            try:
                val = next(it)
                values.append(val)
                all_exhausted = False
            except StopIteration:
                values.append(sentinel)

        if all_exhausted:
            break

        # Check if all are sentinel
        if all(v is sentinel for v in values):
            break

        yield [fillvalue if v is sentinel else v for v in values]


def starmap(fn, iterable):
    """
    Apply fn(*args) for each args in iterable.
    """
    for args in iterable:
        yield fn(*args)


def accumulate(iterable, func=None, *, initial=None):
    """
    Return running totals (or accumulated results using func).
    """
    if func is None:
        func = lambda a, b: a + b

    it = iter(iterable)
    total = initial

    if initial is not None:
        yield initial

    for item in it:
        if total is None:
            total = item
        else:
            total = func(total, item)
        yield total


# --- Invariant test functions ---

def itertools2_groupby():
    """Returns the number of groups when grouping [1,1,2,2]."""
    groups = list(groupby([1, 1, 2, 2]))
    return len(groups)


def itertools2_zip_longest():
    """Returns list of lists from zip_longest([1,2],[3])."""
    result = list(zip_longest([1, 2], [3]))
    return result


def itertools2_starmap():
    """Returns list(starmap(pow, [(2,3),(3,2)]))."""
    return list(starmap(pow, [(2, 3), (3, 2)]))