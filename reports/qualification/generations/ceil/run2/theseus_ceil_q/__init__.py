# generation B ceil class


class _Ceil:
    def __call__(self, x):
        integer = int(x)
        if x > integer:
            return integer + 1
        return integer


def ceil(x):
    return _Ceil()(x)
