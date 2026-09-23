# generation B lcm class


class _Multiple:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def value(self):
        a = self.a
        b = self.b
        if a == 0 or b == 0:
            return 0

        x = abs(a)
        y = abs(b)
        while y:
            x, y = y, x % y
        return abs(a * b) // x


def lcm(a, b):
    return _Multiple(a, b).value()
