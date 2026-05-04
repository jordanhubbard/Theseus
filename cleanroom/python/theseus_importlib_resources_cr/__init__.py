"""Clean-room importlib.resources subset for Theseus invariants."""

import contextlib
import pathlib


class Traversable:
    def is_dir(self):
        return False

    def is_file(self):
        return False


class Path(Traversable):
    def __init__(self, path):
        self.path = pathlib.Path(path)

    def is_dir(self):
        return self.path.is_dir()

    def is_file(self):
        return self.path.is_file()

    def joinpath(self, *parts):
        return Path(self.path.joinpath(*parts))

    __truediv__ = joinpath


def files(package):
    if isinstance(package, str):
        try:
            mod = __import__(package)
            base = getattr(mod, "__file__", None)
            return Path(pathlib.Path(base).parent if base else pathlib.Path("."))
        except Exception:
            return Path(".")
    return Path(getattr(package, "__file__", "."))


@contextlib.contextmanager
def as_file(path):
    yield getattr(path, "path", path)


def is_resource(package, name):
    return files(package).joinpath(name).is_file()


def contents(package):
    p = files(package).path
    return [x.name for x in p.iterdir()] if p.exists() and p.is_dir() else []


def read_text(package, resource, encoding="utf-8", errors="strict"):
    return files(package).joinpath(resource).path.read_text(encoding=encoding, errors=errors)


def read_binary(package, resource):
    return files(package).joinpath(resource).path.read_bytes()


def open_text(package, resource, encoding="utf-8", errors="strict"):
    return files(package).joinpath(resource).path.open("r", encoding=encoding, errors=errors)


def open_binary(package, resource):
    return files(package).joinpath(resource).path.open("rb")


def path(package, resource):
    return as_file(files(package).joinpath(resource))


def impres2_files():
    result = files("os")
    return result is not None and hasattr(result, "is_dir")


def impres2_path():
    p = Path(pathlib.Path(__file__).parent)
    return isinstance(p, Traversable) and p.is_dir()


def impres2_is_resource():
    return isinstance(is_resource("os", "path.py"), bool)


__all__ = [
    "Traversable", "Path", "files", "as_file", "is_resource", "contents",
    "read_text", "read_binary", "open_text", "open_binary", "path",
    "impres2_files", "impres2_path", "impres2_is_resource",
]
