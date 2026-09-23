# generation B trunc class


class _Trunc:
    def apply(self, x):
        return int(x)


_trunc = _Trunc()


def trunc(x):
    return _trunc.apply(x)
