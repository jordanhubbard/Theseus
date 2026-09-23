# generation B logger class


class _Log:
    def __init__(self, name):
        self.name = name


def getLogger(name):
    return _Log(name)
