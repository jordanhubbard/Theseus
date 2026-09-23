# generation B text class


class _Text:
    def __init__(self, text=""):
        self._text = text
        self._position = 0

    def getvalue(self):
        return self._text

    def read(self):
        result = self._text[self._position:]
        self._position = len(self._text)
        return result


StringIO = _Text
