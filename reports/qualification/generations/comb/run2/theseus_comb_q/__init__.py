# generation B choose class

from operator import index

__all__ = ["comb"]


class _Choose:
    def __init__(self, n, k):
        self.n = index(n)
        self.k = index(k)

    def calculate(self):
        n = self.n
        k = self.k
        if n < 0:
            raise ValueError("n must be a non-negative integer")
        if k < 0:
            raise ValueError("k must be a non-negative integer")
        if k > n:
            return 0

        k = min(k, n - k)
        result = 1
        for divisor in range(1, k + 1):
            result = result * (n - k + divisor) // divisor
        return result


def comb(n, k):
    return _Choose(n, k).calculate()
