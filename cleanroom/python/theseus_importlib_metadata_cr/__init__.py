"""Clean-room importlib.metadata subset for Theseus invariants."""


class PackageNotFoundError(ModuleNotFoundError):
    pass


class Metadata(dict):
    pass


class Distribution:
    metadata = Metadata({"Name": "cleanroom", "Version": "0.0"})

    def __init__(self, name="cleanroom"):
        self.name = name
        self.metadata = Metadata({"Name": name, "Version": "0.0"})

    @classmethod
    def from_name(cls, name):
        return cls(name)


class EntryPoint:
    def __init__(self, name="", value="", group=""):
        self.name = name
        self.value = value
        self.group = group


def version(package):
    return "0.0"


def metadata(package):
    return Distribution.from_name(package).metadata


def requires(package):
    return []


def entry_points(**params):
    return []


def files(package):
    return []


def packages_distributions():
    return {}


def impmeta2_version():
    try:
        v = version("pip")
        return isinstance(v, str) and len(v) > 0
    except PackageNotFoundError:
        return True


def impmeta2_packages():
    return isinstance(packages_distributions(), dict)


def impmeta2_distribution():
    return isinstance(Distribution, type) and hasattr(Distribution, "metadata") and hasattr(Distribution, "from_name")


__all__ = [
    "PackageNotFoundError", "Metadata", "Distribution", "EntryPoint",
    "version", "metadata", "requires", "entry_points", "files",
    "packages_distributions", "impmeta2_version", "impmeta2_packages",
    "impmeta2_distribution",
]
