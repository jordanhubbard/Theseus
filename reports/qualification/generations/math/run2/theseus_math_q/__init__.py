# generation B ints class

__all__ = ["factorial", "gcd", "isqrt"]


def _as_index(value):
    if isinstance(value, int):
        return value
    try:
        method = value.__index__
    except AttributeError:
        raise TypeError("integer argument expected")
    result = method()
    if not isinstance(result, int):
        raise TypeError("__index__ returned non-int")
    return result


class _Ints:
    @staticmethod
    def factorial(n):
        n = _as_index(n)
        if n < 0:
            raise ValueError("factorial() not defined for negative values")
        result = 1
        for factor in range(2, n + 1):
            result *= factor
        return result

    @staticmethod
    def gcd(a, b):
        a = abs(_as_index(a))
        b = abs(_as_index(b))
        while b:
            a, b = b, a % b
        return a

    @staticmethod
    def isqrt(n):
        n = _as_index(n)
        if n < 0:
            raise ValueError("isqrt() argument must be nonnegative")
        if n < 2:
            return n

        estimate = 1 << ((n.bit_length() + 1) // 2)
        while True:
            improved = (estimate + n // estimate) // 2
            if improved >= estimate:
                return estimate
            estimate = improved


def factorial(n):
    return _Ints.factorial(n)


def gcd(a, b):
    return _Ints.gcd(a, b)


def isqrt(n):
    return _Ints.isqrt(n)
