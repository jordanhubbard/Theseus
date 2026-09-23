# generation A lcm scan

def _gcd(a, b):
    a = abs(a)
    b = abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    if a == 0 or b == 0:
        return 0
    g = _gcd(a, b)
    return abs(a * b) // g
