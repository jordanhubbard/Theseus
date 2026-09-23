# generation B median class


class _Low:
    def __init__(self, data):
        self._values = sorted(data)

    def result(self):
        return self._values[(len(self._values) - 1) // 2]


def median_low(data):
    return _Low(data).result()
