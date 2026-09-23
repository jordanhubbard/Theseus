# generation B pickle class


class _Pickler:
    def __init__(self, protocol=0):
        if protocol != 0:
            raise ValueError("only protocol 0 is supported")
        self.protocol = protocol

    def dumps(self, obj):
        if (
            not isinstance(obj, list)
            or len(obj) != 1
            or not isinstance(obj[0], int)
            or isinstance(obj[0], bool)
        ):
            raise TypeError("only a one-element list containing an int is supported")
        return b"(lp0\nI" + str(obj[0]).encode("ascii") + b"\na."


def dumps(obj, protocol=0):
    return _Pickler(protocol).dumps(obj)
