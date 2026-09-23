# generation B typed class

import operator


class _Typed:
    def __init__(self, typecode, initializer):
        if typecode not in ("b", "I"):
            raise ValueError("bad typecode")

        lower, upper = (-128, 127) if typecode == "b" else (0, 4294967295)
        items = []
        for item in initializer:
            value = operator.index(item)
            if value < lower or value > upper:
                raise OverflowError("integer out of range")
            items.append(value)

        self.typecode = typecode
        self._items = items

    def tolist(self):
        return list(self._items)


def array(typecode, initializer):
    return _Typed(typecode, initializer)
