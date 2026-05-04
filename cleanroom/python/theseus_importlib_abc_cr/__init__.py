"""Clean-room importlib.abc subset for Theseus invariants."""

import abc


class Finder(metaclass=abc.ABCMeta):
    pass


class MetaPathFinder(Finder):
    def find_spec(self, fullname, path=None, target=None):
        return None


class PathEntryFinder(Finder):
    pass


class Loader(metaclass=abc.ABCMeta):
    pass


class ResourceLoader(Loader):
    pass


class InspectLoader(Loader):
    pass


class ExecutionLoader(InspectLoader):
    pass


class FileLoader(ResourceLoader, ExecutionLoader):
    pass


class SourceLoader(FileLoader):
    pass


class Traversable(metaclass=abc.ABCMeta):
    pass


class TraversableResources(ResourceLoader):
    pass


def importlibabs2_finder():
    return isinstance(Finder, type) and isinstance(MetaPathFinder, type) and isinstance(PathEntryFinder, type)


def importlibabs2_loader():
    return isinstance(Loader, type) and isinstance(ResourceLoader, type) and isinstance(InspectLoader, type)


def importlibabs2_meta_path_finder():
    class TestFinder(MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            return None

    return isinstance(TestFinder(), MetaPathFinder)


__all__ = [
    "Finder", "MetaPathFinder", "PathEntryFinder", "Loader", "ResourceLoader",
    "InspectLoader", "ExecutionLoader", "FileLoader", "SourceLoader",
    "Traversable", "TraversableResources",
    "importlibabs2_finder", "importlibabs2_loader", "importlibabs2_meta_path_finder",
]
