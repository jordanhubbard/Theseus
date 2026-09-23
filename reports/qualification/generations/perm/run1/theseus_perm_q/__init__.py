# generation A perm scan

def perm(n, k=None):
    if not isinstance(n, int):
        raise TypeError
    if k is None:
        k = n
    elif not isinstance(k, int):
        raise TypeError
    if n < 0 or k < 0:
        raise ValueError
    if k > n:
        return 0
    result = 1
    for i in range(n - k + 1, n + 1):
        result *= i
    return result
