# generation B fabs class


class _Abs:
    def __call__(self, x):
        return float(abs(x))


_abs = _Abs()


def fabs(x):
    return _abs(x)
