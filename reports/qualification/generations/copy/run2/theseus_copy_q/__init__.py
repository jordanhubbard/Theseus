# generation B copier class


class _Copier:
    def __init__(self):
        self._memo = {}

    def copy(self, value):
        if isinstance(value, list):
            return list(value)
        if isinstance(value, dict):
            return dict(value)
        return value

    def deepcopy(self, value):
        if isinstance(value, (int, str, type(None), bool, float, bytes)):
            return value

        identity = id(value)
        if identity in self._memo:
            return self._memo[identity]

        if isinstance(value, list):
            result = []
            self._memo[identity] = result
            result.extend(self.deepcopy(item) for item in value)
            return result

        if isinstance(value, dict):
            result = {}
            self._memo[identity] = result
            for key, item in value.items():
                result[self.deepcopy(key)] = self.deepcopy(item)
            return result

        if isinstance(value, tuple):
            result = tuple(self.deepcopy(item) for item in value)
            self._memo[identity] = result
            return result

        return value


def copy(value):
    return _Copier().copy(value)


def deepcopy(value):
    return _Copier().deepcopy(value)
