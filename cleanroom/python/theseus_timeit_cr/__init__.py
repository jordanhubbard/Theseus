"""
theseus_timeit_cr — Clean-room timeit module.
No import of the standard `timeit` module.
"""

import time


def default_timer():
    """Return the default timer (perf_counter)."""
    return time.perf_counter()


class Timer:
    """Timer object for measuring execution time of small code snippets."""

    def __init__(self, stmt='pass', setup='pass', timer=None):
        self.stmt = stmt
        self.setup = setup
        self.timer = timer or default_timer

    def timeit(self, number=1000000):
        """Time execution of stmt, running number times. Return total seconds."""
        # Execute setup once
        if self.setup != 'pass':
            exec(self.setup, {})

        ns = {}
        if self.setup != 'pass':
            exec(self.setup, ns)

        start = self.timer()
        for _ in range(number):
            exec(self.stmt, ns)
        end = self.timer()
        return end - start

    def repeat(self, repeat=5, number=1000000):
        """Call timeit() repeat times, return list of results."""
        return [self.timeit(number) for _ in range(repeat)]

    def autorange(self, callback=None):
        """Determine number of iterations for timeit to take ~0.2s."""
        i = 1
        while True:
            for j in 1, 2, 5:
                number = i * j
                t = self.timeit(number)
                if callback:
                    callback(number, t)
                if t >= 0.2:
                    return number, t
            i *= 10


def timeit(stmt='pass', setup='pass', number=1000000, globals=None):
    """Convenience function to create Timer object and call timeit()."""
    t = Timer(stmt, setup)
    return t.timeit(number)


def repeat(stmt='pass', setup='pass', repeat=5, number=1000000, globals=None):
    """Convenience function to create Timer object and call repeat()."""
    t = Timer(stmt, setup)
    return t.repeat(repeat, number)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def timeit2_basic():
    """timeit('pass', number=1000) returns non-negative float; returns True."""
    t = timeit('pass', number=1000)
    return isinstance(t, float) and t >= 0


def timeit2_repeat():
    """repeat('pass', number=10, repeat=3) returns list of 3 floats; returns 3."""
    r = repeat('pass', number=10, repeat=3)
    return len(r)


def timeit2_timer_callable():
    """Timer('1+1').timeit(number=10) returns non-negative float; returns True."""
    t = Timer('1+1').timeit(number=10)
    return isinstance(t, float) and t >= 0


__all__ = [
    'Timer', 'timeit', 'repeat', 'default_timer',
    'timeit2_basic', 'timeit2_repeat', 'timeit2_timer_callable',
]
