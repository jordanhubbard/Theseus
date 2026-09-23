# generation B isqrt class


class _Root:
    def __init__(self, n):
        try:
            value = n.__index__()
        except AttributeError:
            raise TypeError("isqrt() argument must be an integer")
        if not isinstance(value, int):
            raise TypeError("__index__ returned non-int")
        if value < 0:
            raise ValueError("isqrt() argument must be nonnegative")
        self._n = value

    def calculate(self):
        if self._n < 2:
            return self._n

        estimate = 1 << ((self._n.bit_length() + 1) // 2)
        while True:
            next_estimate = (estimate + self._n // estimate) // 2
            if next_estimate >= estimate:
                return estimate
            estimate = next_estimate


def isqrt(n):
    return _Root(n).calculate()
