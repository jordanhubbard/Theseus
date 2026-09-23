# generation B sem class


class _Sem:
    def __init__(self, value=1):
        self._value = value

    def acquire(self, blocking=True):
        if self._value > 0:
            self._value -= 1
            return True
        return False


Semaphore = _Sem
