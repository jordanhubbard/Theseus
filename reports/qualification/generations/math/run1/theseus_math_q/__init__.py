# generation A integer math


def factorial(n):
    if n < 0:
        raise ValueError("factorial() not defined for negative values")
    result = 1
    for k in range(2, n + 1):
        result *= k
    return result


def gcd(a, b):
    a = abs(a)
    b = abs(b)
    while b:
        a, b = b, a % b
    return a


def isqrt(n):
    if n < 0:
        raise ValueError("isqrt() argument must be nonnegative")
    if n < 2:
        return n
    low = 1
    high = n
    while low < high:
        mid = (low + high + 1) // 2
        if mid * mid <= n:
            low = mid
        else:
            high = mid - 1
    return low
