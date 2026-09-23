# generation A text scan

__all__ = ["StringIO"]


class StringBuffer(object):
    def __init__(self, text):
        self.text = text


class StringIO(object):
    def __init__(self, initial_value=""):
        if initial_value is None:
            initial_value = ""
        self._buf = StringBuffer(str(initial_value))
        self._pos = 0

    def getvalue(self):
        return self._buf.text

    def read(self, size=-1):
        text = self._buf.text
        if size is None or size < 0:
            chunk = text[self._pos:]
            self._pos = len(text)
            return chunk
        end = self._pos + size
        chunk = text[self._pos:end]
        self._pos += len(chunk)
        return chunk
