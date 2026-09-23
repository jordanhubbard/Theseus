# generation B hypot class


class _Hypot:
    def __call__(self, x, y):
        a = abs(float(x))
        b = abs(float(y))
        infinity = float("inf")

        if a == infinity or b == infinity:
            return infinity
        if a != a or b != b:
            return float("nan")
        if b > a:
            a, b = b, a
        if a == 0.0:
            return 0.0

        ratio = b / a
        return float(a * (1.0 + ratio * ratio) ** 0.5)


_hypot = _Hypot()


def hypot(x, y):
    return _hypot(x, y)
