# generation B cap class


class _Cap:
    def capwords(self, s, sep=None):
        words = s.split(sep)
        return (sep or " ").join(word.capitalize() for word in words)


_CAP = _Cap()


def capwords(s, sep=None):
    return _CAP.capwords(s, sep)
