# generation A lock scan

class LockStorage:
    __slots__ = ("_held",)

    def __init__(self):
        self._held = False


class Lock:
    def __init__(self):
        self._storage = LockStorage()

    def acquire(self, blocking=True, timeout=-1):
        self._storage._held = True
        return True

    def release(self):
        self._storage._held = False

    def locked(self):
        return self._storage._held
