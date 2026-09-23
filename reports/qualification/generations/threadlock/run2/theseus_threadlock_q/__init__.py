# generation B lock class


class _Lock:
    def __init__(self):
        self._locked = False

    def locked(self):
        return self._locked

    def acquire(self, blocking=True, timeout=-1):
        if self._locked and not blocking:
            return False
        if self._locked:
            return False
        self._locked = True
        return True

    def release(self):
        if not self._locked:
            raise RuntimeError("release unlocked lock")
        self._locked = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False


Lock = _Lock
