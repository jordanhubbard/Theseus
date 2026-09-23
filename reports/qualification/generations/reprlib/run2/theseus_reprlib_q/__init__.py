# generation B limited class


class _Limited:
    def __init__(self):
        self.maxlist = 6
        self.maxstring = 30

    def formats(self, value):
        if isinstance(value, list):
            items = [self.formats(item) for item in value[:self.maxlist]]
            if len(value) > self.maxlist:
                items.append("...")
            return "[" + ", ".join(items) + "]"
        if isinstance(value, str):
            text = value.__repr__()
            if len(text) <= self.maxstring:
                return text
            left = (self.maxstring - 3) // 2
            right = self.maxstring - 3 - left
            shortened = (value[:left] + value[-right:]).__repr__()
            return shortened[:left] + "..." + shortened[-right:]
        return value.__repr__()


def repr(obj):
    return _Limited().formats(obj)
