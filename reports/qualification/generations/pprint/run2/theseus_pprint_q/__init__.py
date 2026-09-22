# generation B pretty class


class _Pretty:
    def __init__(self, sort_dicts=True):
        self.sort_dicts = sort_dicts

    def format(self, value):
        if isinstance(value, list):
            return "[" + ", ".join(self.format(item) for item in value) + "]"
        if isinstance(value, dict):
            items = value.items()
            if self.sort_dicts:
                items = sorted(items, key=lambda item: item[0])
            return (
                "{"
                + ", ".join(
                    self.format(key) + ": " + self.format(item)
                    for key, item in items
                )
                + "}"
            )
        if value is None or isinstance(value, (bool, int, str)):
            return repr(value)
        return repr(value)


def pformat(obj, sort_dicts=True):
    return _Pretty(sort_dicts=sort_dicts).format(obj)
