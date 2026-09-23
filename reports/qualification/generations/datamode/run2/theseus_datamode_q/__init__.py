# generation B mode class

__all__ = ["mode"]


class _Mode:
    def __init__(self, data):
        self._data = list(data)

    def result(self):
        if not self._data:
            raise ValueError("no mode for empty data")

        best_value = self._data[0]
        best_count = 0
        for candidate in self._data:
            count = sum(value == candidate for value in self._data)
            if count > best_count:
                best_value = candidate
                best_count = count
        return best_value


def mode(data):
    return _Mode(data).result()
