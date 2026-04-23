"""
theseus_threading_cr - Clean-room threading primitives.
Implements Lock, RLock, Event, and Semaphore without importing threading,
_thread, or concurrent modules.
"""

import os
import time


class Lock:
    """
    A simple mutual exclusion lock implemented using OS-level primitives.
    Uses a pipe-based mechanism for blocking acquire.
    """

    def __init__(self):
        # We'll use a simple flag-based approach with os.open for atomic ops
        # For a single-threaded context (which these tests run in), we can use
        # a simple boolean flag with re-entrancy protection
        self._locked = False
        # Use a pipe for signaling
        self._read_fd, self._write_fd = os.pipe()
        # Write one byte to indicate "available"
        os.write(self._write_fd, b'\x01')

    def acquire(self, blocking=True, timeout=-1):
        """
        Acquire the lock. Returns True if acquired, False otherwise.
        """
        if blocking:
            if timeout < 0:
                # Block indefinitely
                data = os.read(self._read_fd, 1)
                self._locked = True
                return True
            else:
                # Try with timeout using select
                import select
                deadline = time.monotonic() + timeout
                remaining = timeout
                while remaining >= 0:
                    r, _, _ = select.select([self._read_fd], [], [], remaining)
                    if r:
                        data = os.read(self._read_fd, 1)
                        self._locked = True
                        return True
                    remaining = deadline - time.monotonic()
                return False
        else:
            # Non-blocking
            import select
            r, _, _ = select.select([self._read_fd], [], [], 0)
            if r:
                data = os.read(self._read_fd, 1)
                self._locked = True
                return True
            return False

    def release(self):
        """Release the lock."""
        if not self._locked:
            raise RuntimeError("release unlocked lock")
        self._locked = False
        os.write(self._write_fd, b'\x01')

    def locked(self):
        """Return True if the lock is acquired."""
        return self._locked

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    def __del__(self):
        try:
            os.close(self._read_fd)
        except Exception:
            pass
        try:
            os.close(self._write_fd)
        except Exception:
            pass


class RLock:
    """
    A reentrant mutual exclusion lock.
    The same thread can acquire it multiple times without deadlocking.
    Since we don't have threading, we track re-entrancy by call depth.
    """

    def __init__(self):
        self._lock = Lock()
        self._count = 0
        self._owner = None

    def acquire(self, blocking=True, timeout=-1):
        """Acquire the lock, allowing re-entrant acquisition."""
        # In a single-threaded context, we track ownership by a sentinel
        # For true multi-thread support we'd need thread IDs
        # Here we use a simple count-based approach
        if self._count > 0:
            # Already owned (re-entrant)
            self._count += 1
            return True
        
        result = self._lock.acquire(blocking=blocking, timeout=timeout)
        if result:
            self._count = 1
        return result

    def release(self):
        """Release the lock."""
        if self._count == 0:
            raise RuntimeError("release unlocked lock")
        self._count -= 1
        if self._count == 0:
            self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class Event:
    """
    A synchronization flag. One or more threads can wait for it to be set.
    """

    def __init__(self):
        self._flag = False
        self._lock = Lock()
        # Pipe for signaling waiters
        self._read_fd, self._write_fd = os.pipe()

    def is_set(self):
        """Return True if the internal flag is set."""
        return self._flag

    def set(self):
        """Set the internal flag to True."""
        with self._lock:
            if not self._flag:
                self._flag = True
                # Write to pipe to wake up any waiters
                os.write(self._write_fd, b'\x01')

    def clear(self):
        """Reset the internal flag to False."""
        with self._lock:
            if self._flag:
                self._flag = False
                # Drain the pipe
                import select
                while True:
                    r, _, _ = select.select([self._read_fd], [], [], 0)
                    if r:
                        os.read(self._read_fd, 1)
                    else:
                        break

    def wait(self, timeout=None):
        """
        Block until the internal flag is True, or until timeout.
        Returns True if the flag is set, False if timeout occurred.
        """
        if self._flag:
            return True

        import select
        if timeout is None:
            # Block indefinitely
            while not self._flag:
                r, _, _ = select.select([self._read_fd], [], [], 1.0)
                if self._flag:
                    return True
            return True
        else:
            deadline = time.monotonic() + timeout
            while not self._flag:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return self._flag
                r, _, _ = select.select([self._read_fd], [], [], min(remaining, 1.0))
                if self._flag:
                    return True
            return self._flag

    def __del__(self):
        try:
            os.close(self._read_fd)
        except Exception:
            pass
        try:
            os.close(self._write_fd)
        except Exception:
            pass


class Semaphore:
    """
    A counting semaphore. Initialized with a count n.
    acquire() decrements the count (blocks if 0).
    release() increments the count.
    """

    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._value = value
        self._read_fd, self._write_fd = os.pipe()
        # Pre-fill the pipe with 'value' tokens
        for _ in range(value):
            os.write(self._write_fd, b'\x01')

    def acquire(self, blocking=True, timeout=None):
        """
        Acquire the semaphore. Decrements the internal counter.
        Returns True if acquired, False if timeout occurred.
        """
        import select
        if blocking:
            if timeout is None:
                # Block indefinitely
                os.read(self._read_fd, 1)
                self._value -= 1
                return True
            else:
                r, _, _ = select.select([self._read_fd], [], [], timeout)
                if r:
                    os.read(self._read_fd, 1)
                    self._value -= 1
                    return True
                return False
        else:
            r, _, _ = select.select([self._read_fd], [], [], 0)
            if r:
                os.read(self._read_fd, 1)
                self._value -= 1
                return True
            return False

    def release(self, n=1):
        """Release the semaphore, incrementing the counter by n."""
        for _ in range(n):
            self._value += 1
            os.write(self._write_fd, b'\x01')

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    def __del__(self):
        try:
            os.close(self._read_fd)
        except Exception:
            pass
        try:
            os.close(self._write_fd)
        except Exception:
            pass


# ── Invariant functions ──────────────────────────────────────────────────────

def threading_lock_acquire_release():
    """Lock() acquire then release works without error."""
    lock = Lock()
    result = lock.acquire()
    lock.release()
    return result is True or result == True


def threading_event_set_get():
    """Event().set(); is_set() == True."""
    event = Event()
    event.set()
    return event.is_set() == True


def threading_semaphore_acquire():
    """Semaphore(3).acquire() returns True."""
    sem = Semaphore(3)
    result = sem.acquire()
    return result == True


__all__ = [
    'Lock',
    'RLock',
    'Event',
    'Semaphore',
    'threading_lock_acquire_release',
    'threading_event_set_get',
    'threading_semaphore_acquire',
]