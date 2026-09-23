# generation B perm class


class _Order:
    @staticmethod
    def _integer(value):
        if isinstance(value, int):
            return int(value)
        method = getattr(type(value), "__index__", None)
        if method is None:
            raise TypeError(
                "'{}' object cannot be interpreted as an integer".format(
                    type(value).__name__
                )
            )
        result = method(value)
        if not isinstance(result, int):
            raise TypeError("__index__ returned non-int")
        return int(result)

    def perm(self, n, k):
        n = self._integer(n)
        k = self._integer(k)
        if n < 0 or k < 0:
            raise ValueError("perm() not defined for negative values")
        if k > n:
            return 0

        result = 1
        factor = n
        for _ in range(k):
            result *= factor
            factor -= 1
        return result


_ORDER = _Order()


def perm(n, k):
    return _ORDER.perm(n, k)
