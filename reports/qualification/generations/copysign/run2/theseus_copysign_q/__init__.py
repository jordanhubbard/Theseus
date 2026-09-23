# generation B sign class


class _Sign:
    def copy(self, x, y):
        magnitude = abs(float(x))
        if float(y) < 0.0:
            return -magnitude
        return magnitude


def copysign(x, y):
    return _Sign().copy(x, y)
