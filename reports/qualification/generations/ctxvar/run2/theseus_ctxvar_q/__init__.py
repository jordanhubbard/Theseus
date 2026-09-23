# generation B context class


class _Var:
    def __init__(self, name, *, default=None):
        self.name = name
        self._default = default

    def get(self):
        return self._default


ContextVar = _Var
