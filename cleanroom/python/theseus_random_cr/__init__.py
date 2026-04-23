"""
theseus_random_cr: Clean-room pseudo-random number generator.
Implements an LCG (Linear Congruential Generator).
"""

import os
import struct

# LCG parameters (same as Numerical Recipes / glibc)
_LCG_A = 1664525
_LCG_C = 1013904223
_LCG_M = 2**32  # modulus

# Seed from os.urandom
def _get_seed():
    raw = os.urandom(4)
    return struct.unpack('>I', raw)[0]

_state = _get_seed()


def _next_state():
    global _state
    _state = (_LCG_A * _state + _LCG_C) % _LCG_M
    return _state


def random() -> float:
    """Return a random float in [0.0, 1.0)."""
    val = _next_state()
    return val / _LCG_M


def randint(a: int, b: int) -> int:
    """Return a random integer N such that a <= N <= b."""
    if a > b:
        raise ValueError("a must be <= b")
    range_size = b - a + 1
    return a + (_next_state() % range_size)


def choice(seq):
    """Return a uniformly random element from a non-empty sequence."""
    if len(seq) == 0:
        raise IndexError("Cannot choose from an empty sequence")
    idx = _next_state() % len(seq)
    return seq[idx]


def shuffle(seq: list) -> None:
    """In-place shuffle of a list using Fisher-Yates algorithm."""
    n = len(seq)
    for i in range(n - 1, 0, -1):
        j = _next_state() % (i + 1)
        seq[i], seq[j] = seq[j], seq[i]


# --- Invariant-satisfying helper functions ---

def random_randint_range() -> bool:
    """randint(1, 10) returns int in [1, 10]."""
    val = randint(1, 10)
    return isinstance(val, int) and 1 <= val <= 10


def random_choice_valid() -> bool:
    """choice([1,2,3,4,5]) returns one of those values."""
    options = [1, 2, 3, 4, 5]
    val = choice(options)
    return val in options


def random_shuffle_len() -> bool:
    """shuffle([1,2,3]) preserves length."""
    lst = [1, 2, 3]
    shuffle(lst)
    return len(lst) == 3


def random_shuffle_preserves_elements() -> bool:
    """shuffle preserves all elements (just reorders them)."""
    original = [1, 2, 3, 4, 5]
    lst = original[:]
    shuffle(lst)
    return sorted(lst) == sorted(original) and len(lst) == len(original)