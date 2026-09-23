# generation A choose scan

def comb(n, k):
    if not isinstance(n, int):
        raise TypeError(
            "'{}' object cannot be interpreted as an integer".format(type(n).__name__)
        )
    if not isinstance(k, int):
        raise TypeError(
            "'{}' object cannot be interpreted as an integer".format(type(k).__name__)
        )
    if n < 0:
        raise ValueError("n must be a non-negative integer")
    if k < 0:
        raise ValueError("k must be a non-negative integer")
    if k > n:
        return 0
    if k > n - k:
        k = n - k
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result
