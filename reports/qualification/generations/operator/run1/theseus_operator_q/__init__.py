# generation A operator funcs.

def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def getitem(a, b):
    return a[b]


def itemgetter(*items):
    if not items:
        raise TypeError("itemgetter expected 1 argument, got 0")
    if len(items) == 1:
        item = items[0]

        def getter(obj):
            return obj[item]

        return getter

    def getter(obj):
        return tuple(obj[item] for item in items)

    return getter


__all__ = ["add", "sub", "mul", "getitem", "itemgetter"]
