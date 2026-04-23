def all_(iterable):
    """Return True if all elements of the iterable are truthy (or iterable is empty)."""
    for element in iterable:
        if not element:
            return False
    return True


def any_(iterable):
    """Return True if any element of the iterable is truthy."""
    for element in iterable:
        if element:
            return True
    return False


def zip_(*iterables):
    """Yield tuples from parallel iterables, stopping at the shortest."""
    iterators = [iter(it) for it in iterables]
    while True:
        result = []
        for iterator in iterators:
            try:
                value = next(iterator)
            except StopIteration:
                return
            result.append(value)
        yield tuple(result)


def enumerate_(iterable, start=0):
    """Yield (index, value) pairs starting from start."""
    index = start
    for value in iterable:
        yield (index, value)
        index += 1


def builtins_all_true():
    """all_([1, 2, 3]) == True"""
    return all_([1, 2, 3]) == True


def builtins_any_false():
    """any_([0, 0, 1]) == True"""
    return any_([0, 0, 1]) == True


def builtins_zip():
    """list(zip_([1,2],[3,4])) == [(1,3),(2,4)] returns True"""
    return list(zip_([1, 2], [3, 4])) == [(1, 3), (2, 4)]


def builtins_enumerate():
    """list(enumerate_(['a','b']))[0] == (0,'a') returns True"""
    return list(enumerate_(['a', 'b']))[0] == (0, 'a')