# generation B ops class


class _Ops:
    @staticmethod
    def add(a, b):
        return a + b

    @staticmethod
    def sub(a, b):
        return a - b

    @staticmethod
    def mul(a, b):
        return a * b


add = _Ops.add
sub = _Ops.sub
mul = _Ops.mul


def getitem(obj, key):
    return obj[key]


class itemgetter:
    __slots__ = ("_items",)

    def __init__(self, item, *items):
        self._items = (item,) + items

    def __call__(self, obj):
        if len(self._items) == 1:
            return obj[self._items[0]]
        return tuple(obj[item] for item in self._items)

    def __repr__(self):
        arguments = ", ".join(repr(item) for item in self._items)
        return "operator.itemgetter({})".format(arguments)
