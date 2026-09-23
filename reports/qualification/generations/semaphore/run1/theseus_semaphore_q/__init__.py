# generation A sem scan

class PermitBucket(object):
    def __init__(self, count):
        self.count = count


class Semaphore(object):
    def __init__(self, value=1):
        if value < 0:
            raise ValueError("semaphore initial value must be >= 0")
        self._permits = PermitBucket(value)

    def acquire(self, blocking=True, timeout=-1):
        if self._permits.count > 0:
            self._permits.count -= 1
            return True
        if not blocking:
            return False
        while self._permits.count <= 0:
            pass
        self._permits.count -= 1
        return True
