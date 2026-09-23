# generation B posix class


class _Posix:
    def __init__(self, text):
        self._text = str(text)

    @property
    def name(self):
        path = self._text.rstrip("/")
        if not path:
            return ""
        return path.rsplit("/", 1)[-1]

    @property
    def suffix(self):
        name = self.name
        dot = name.rfind(".")
        if dot <= 0 or dot == len(name) - 1:
            return ""
        return name[dot:]

    def __str__(self):
        return self._text


def PurePosixPath(text):
    return _Posix(text)
