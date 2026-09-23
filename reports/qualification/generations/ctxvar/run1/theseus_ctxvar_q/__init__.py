# generation A context scan

__all__ = ["ContextVar"]


class ContextCell(object):
    __slots__ = ("default",)

    def __init__(self, default):
        self.default = default


class ContextVar(object):
    def __init__(self, name, default=None):
        self.name = name
        self._cell = ContextCell(default)

    def get(self):
        return self._cell.default
