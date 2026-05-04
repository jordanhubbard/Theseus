"""Tiny clean-room pickle-like codec for Theseus invariants."""

import ast

HIGHEST_PROTOCOL = 5
DEFAULT_PROTOCOL = 4
_MAGIC = b"\x80\x04"


class PickleError(Exception):
    pass


class PicklingError(PickleError):
    pass


class UnpicklingError(PickleError):
    pass


def dumps(obj, protocol=None, *, fix_imports=True, buffer_callback=None):
    return _MAGIC + repr(obj).encode("utf-8")


def loads(data, *, fix_imports=True, encoding="ASCII", errors="strict", buffers=None):
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("a bytes-like object is required")
    data = bytes(data)
    if data.startswith(_MAGIC):
        data = data[len(_MAGIC):]
    try:
        return ast.literal_eval(data.decode("utf-8"))
    except Exception as exc:
        raise UnpicklingError(str(exc))


dump = lambda obj, file, protocol=None, **kwargs: file.write(dumps(obj, protocol, **kwargs))
load = lambda file, **kwargs: loads(file.read(), **kwargs)


def pickle2_roundtrip():
    obj = {"a": 1, "b": [2, 3]}
    return loads(dumps(obj)) == obj


def pickle2_list():
    return loads(dumps([1, 2, 3])) == [1, 2, 3]


def pickle2_protocol():
    return isinstance(dumps({"x": 1}, protocol=4), bytes) and dumps([], protocol=4).startswith(_MAGIC)


__all__ = [
    "dump", "dumps", "load", "loads",
    "PickleError", "PicklingError", "UnpicklingError",
    "HIGHEST_PROTOCOL", "DEFAULT_PROTOCOL",
    "pickle2_roundtrip", "pickle2_list", "pickle2_protocol",
]
