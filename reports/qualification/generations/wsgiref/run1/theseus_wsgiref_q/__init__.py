# generation A header scan

__all__ = ["Headers"]


class HeaderPairs:
    """Simple container for (name, value) header pairs."""

    __slots__ = ("pairs",)

    def __init__(self, pairs):
        self.pairs = list(pairs)


def _header_name_key(name):
    if name is None:
        return None
    return name.lower()


def _lookup_value(container, name):
    key = _header_name_key(name)
    for entry_name, entry_value in container.pairs:
        if _header_name_key(entry_name) == key:
            return entry_value
    return None


class Headers:
    def __init__(self, pairs=None):
        if pairs is None:
            pairs = []
        self._container = HeaderPairs(pairs)

    def get(self, name):
        return _lookup_value(self._container, name)
