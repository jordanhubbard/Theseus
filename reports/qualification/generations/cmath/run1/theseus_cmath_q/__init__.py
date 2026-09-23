# generation A phase scan

import math


def phase(x):
    z = complex(x)
    return math.atan2(z.imag, z.real)
