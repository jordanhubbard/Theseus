# generation B header class


class _Headers:
    def __init__(self, pairs):
        self._pairs = list(pairs)

    def get(self, name):
        target = name.lower()
        for header_name, value in self._pairs:
            if header_name.lower() == target:
                return value
        return None


Headers = _Headers
