# generation B phase class
import math

__all__ = ["phase"]


class _Phase:
    def compute(self, x):
        value = complex(x)
        return math.atan2(value.imag, value.real)


_phase = _Phase()


def phase(x):
    return _phase.compute(x)
