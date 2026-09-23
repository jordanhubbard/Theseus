# generation A tar scan


class _MemberRecord(object):
    def __init__(self, name):
        self.name = name


class TarInfo(object):
    def __init__(self, name):
        self._member = _MemberRecord(name)

    @property
    def name(self):
        return self._member.name
