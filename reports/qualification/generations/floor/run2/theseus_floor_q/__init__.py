# generation B floor class


class _Floor:
    def __call__(self, x):
        integer = int(x)
        if x < integer:
            return integer - 1
        return integer


_floor = _Floor()


def floor(x):
    return _floor(x)
