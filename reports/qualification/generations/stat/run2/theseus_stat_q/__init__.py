# generation B mode class


class _Modes:
    _TYPE_MASK = 0o170000
    _TYPE_CHARS = {
        0o100000: "-",
        0o040000: "d",
    }
    _PERMISSION_BITS = (
        (0o400, "r"),
        (0o200, "w"),
        (0o100, "x"),
        (0o040, "r"),
        (0o020, "w"),
        (0o010, "x"),
        (0o004, "r"),
        (0o002, "w"),
        (0o001, "x"),
    )

    def __init__(self, mode):
        self.mode = mode

    def filemode(self):
        type_char = self._TYPE_CHARS.get(self.mode & self._TYPE_MASK, "?")
        permissions = "".join(
            char if self.mode & bit else "-"
            for bit, char in self._PERMISSION_BITS
        )
        return type_char + permissions


def filemode(mode):
    return _Modes(mode).filemode()
