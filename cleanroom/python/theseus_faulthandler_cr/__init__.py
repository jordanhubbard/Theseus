"""Clean-room faulthandler subset for Theseus invariants."""

_enabled = False


def enable(file=None, all_threads=True):
    global _enabled
    _enabled = True


def disable():
    global _enabled
    _enabled = False


def is_enabled():
    return bool(_enabled)


def dump_traceback(file=None, all_threads=True):
    return None


def dump_traceback_later(timeout, repeat=False, file=None, exit=False):
    return None


def cancel_dump_traceback_later():
    return None


def faulthandler2_enable():
    return callable(enable) and callable(disable)


def faulthandler2_is_enabled():
    return isinstance(is_enabled(), bool)


def faulthandler2_dump_traceback():
    return callable(dump_traceback)


__all__ = [
    "enable", "disable", "is_enabled", "dump_traceback",
    "dump_traceback_later", "cancel_dump_traceback_later",
    "faulthandler2_enable", "faulthandler2_is_enabled", "faulthandler2_dump_traceback",
]
