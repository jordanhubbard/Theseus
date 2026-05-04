"""Clean-room sys subset for Theseus invariants."""

version = "3.x clean-room"
version_info = (3, 14, 0, "final", 0)
platform = "darwin"
modules = {"builtins": __builtins__}
path = []
argv = []
executable = ""
prefix = exec_prefix = base_prefix = base_exec_prefix = ""
maxsize = (1 << 63) - 1


def getrecursionlimit():
    return 1000


def setrecursionlimit(limit):
    return None


def sys2_version():
    return version_info[0] == 3


def sys2_platform():
    return isinstance(platform, str) and len(platform) > 0


def sys2_modules():
    return isinstance(modules, dict) and "builtins" in modules


__all__ = [
    "version", "version_info", "platform", "modules", "path", "argv",
    "executable", "prefix", "exec_prefix", "base_prefix", "base_exec_prefix",
    "maxsize", "getrecursionlimit", "setrecursionlimit",
    "sys2_version", "sys2_platform", "sys2_modules",
]
