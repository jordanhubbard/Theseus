"""
theseus_threading_cr2 - Clean-room synchronization primitives (no actual threads).
"""


class Event:
    """Manual-reset event with set/clear/is_set/wait."""

    def __init__(self):
        self._flag = False

    def set(self):
        """Set the internal flag to True."""
        self._flag = True

    def clear(self):
        """Reset the internal flag to False."""
        self._flag = False

    def is_set(self):
        """Return True if the internal flag is set."""
        return self._flag

    def wait(self, timeout=None):
        """
        Block until the internal flag is True.
        Since this is a clean-room (no actual threads), the flag must already
        be set for wait to return True; otherwise returns False (timeout).
        Returns True if the flag is set, False otherwise.
        """
        return self._flag


class Barrier:
    """
    N-party barrier. wait() blocks until n parties arrive.
    In a single-threaded clean-room implementation, we simulate arrival counting.
    """

    def __init__(self, parties, action=None, timeout=None):
        if parties < 1:
            raise ValueError("parties must be >= 1")
        self._parties = parties
        self._action = action
        self._timeout = timeout
        self._count = 0
        self._phase = 0
        self._broken = False

    @property
    def parties(self):
        return self._parties

    @property
    def n_waiting(self):
        return self._count

    @property
    def broken(self):
        return self._broken

    def wait(self, timeout=None):
        """
        Wait for all parties to arrive.
        Returns the arrival index (0 to parties-1).
        In clean-room single-threaded mode, each call increments the counter.
        When the count reaches parties, the barrier resets and action is called.
        """
        if self._broken:
            raise BrokenBarrierError("Barrier is broken")

        index = self._count
        self._count += 1

        if self._count == self._parties:
            # All parties have arrived
            if self._action is not None:
                try:
                    self._action()
                except Exception:
                    self._broken = True
                    self._count = 0
                    raise BrokenBarrierError("Action raised an exception")
            self._count = 0
            self._phase += 1
            return index
        else:
            # In single-threaded mode, if not all parties arrived yet,
            # we cannot actually block. Return the index anyway.
            # This simulates the case where parties=1 always completes immediately.
            return index

    def reset(self):
        """Reset the barrier to its initial state."""
        self._count = 0
        self._broken = False

    def abort(self):
        """Break the barrier."""
        self._broken = True


class BrokenBarrierError(Exception):
    """Raised when a Barrier is broken."""
    pass


class BoundedSemaphore:
    """
    Like Semaphore but raises ValueError if released more than initial value times.
    """

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._initial_value = value
        self._value = value

    def acquire(self, blocking=True, timeout=None):
        """
        Acquire the semaphore.
        In clean-room single-threaded mode, if value > 0, decrement and return True.
        Otherwise return False (or raise if blocking with no timeout).
        """
        if self._value > 0:
            self._value -= 1
            return True
        return False

    def release(self, n=1):
        """
        Release the semaphore.
        Raises ValueError if the value would exceed the initial value.
        """
        if self._value + n > self._initial_value:
            raise ValueError(
                "BoundedSemaphore released too many times"
            )
        self._value += n

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    @property
    def _Semaphore__value(self):
        return self._value


class Condition:
    """
    Condition variable with wait/notify/notify_all.
    Clean-room implementation without actual threads.
    """

    def __init__(self, lock=None):
        self._lock = lock
        self._waiters = []

    def acquire(self, *args, **kwargs):
        if self._lock is not None:
            return self._lock.acquire(*args, **kwargs)
        return True

    def release(self):
        if self._lock is not None:
            return self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    def wait(self, timeout=None):
        """
        Wait until notified.
        In single-threaded clean-room mode, this cannot actually block.
        Returns True.
        """
        return True

    def wait_for(self, predicate, timeout=None):
        """
        Wait until predicate returns True.
        In single-threaded mode, just check the predicate.
        """
        return predicate()

    def notify(self, n=1):
        """Wake up one or more waiting threads (no-op in single-threaded mode)."""
        pass

    def notify_all(self):
        """Wake up all waiting threads (no-op in single-threaded mode)."""
        pass


# --- Test/demo functions referenced in invariants ---

def threading2_event():
    """
    Create an Event, set it, and return is_set() == True.
    Invariant: threading2_event() → true
    """
    e = Event()
    e.set()
    return e.is_set()


def threading2_barrier():
    """
    Create a Barrier(1), call wait(), return the result (should be 0).
    Invariant: threading2_barrier() → 0
    """
    b = Barrier(1)
    result = b.wait()
    return result


def threading2_bounded_semaphore():
    """
    Create BoundedSemaphore(1), acquire(), release() ok, extra release raises.
    Invariant: threading2_bounded_semaphore() → true
    """
    bs = BoundedSemaphore(1)
    acquired = bs.acquire()
    if not acquired:
        return False
    bs.release()  # This should be fine
    try:
        bs.release()  # This should raise ValueError
        return False  # Should not reach here
    except ValueError:
        return True


__all__ = [
    "Event",
    "Barrier",
    "BrokenBarrierError",
    "BoundedSemaphore",
    "Condition",
    "threading2_event",
    "threading2_barrier",
    "threading2_bounded_semaphore",
]